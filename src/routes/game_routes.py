"""Routes for accessing, monitoring or playing campaign. Also will settle accordingly with an exam trigger.
"""
import random
import flask
from flask import Flask, request, url_for
import traceback 

from src.campaign import * # clamp down later
from src.session import current_data
from src.session import create_campaign_session, build_order_quiz, access_order_quiz, submit_order_quiz_result

import logging 
logger = logging.getLogger(__name__)

from typing import Optional, List, Tuple, Any, Union, Dict 

def build_game_routes(app: Flask, login_decorator: callable=lambda f: f) -> Tuple[Dict, Flask]:
    # campaign management here 
    campaign_data = {}
    @app.route("/play", methods=["GET", "POST"])
    def play():
        if "map" not in campaign_data or request.args.get("redo", "false").lower() == "true":
            logger.debug("Create new campaign map")
            # give 0 a superior bot 
            def PrioritizedBot(player_id, *args, **kwargs):
                if player_id == 1:
                    logger.debug("Allegedly better bot for player 1")
                    # combined variant between FrontlineBot & LandGrabBot; need tweaking for coef
                    return SecureFrontlineBot(player_id, aspects=[TerrainAwarenessAspect(), ExplorerAspect(), CoalitionAspect()], debug=True, *args, **kwargs)
                elif player_id == 3:
                    logger.debug("Rogue bot for player 3.")
                    return FrontlineBot(player_id, *args, **kwargs)
                else:
                    logger.debug("Normal bot for player {:d}".format(player_id))
                    return FrontlineBot(player_id, aspects=[CoalitionAspect()], *args, **kwargs) 
            name_generator_cue = request.args.get("name_type", "gook").lower()
            name_generator_class = NAME_GENERATOR_BY_CUE[name_generator_cue]
            campaign_data["map"] = campaign = PlayerCampaign(players=[0], player_names=["Glorious Green", "Revolutionary Red", "Confidential Cyan", "Brash Beige"], colorscheme=["yellowgreen", "salmon", "powderblue", "moccasin"], bot_class=PrioritizedBot, name_generator=name_generator_class(shared_kwargs={"filter_generation_rule": True}), rules=[TerrainRule, CoreRule, ScorchedRule, RandomFactorRule, ExhaustionRule], flavor_text=DefaultFlavorText)
            # similarly, create a symbiotic session 
            # random 4 category 
            categories = random.sample(current_data.categories, k=min(4, len(current_data.categories)))
            logger.debug("Creating session with categories: {}".format(categories))
            campaign_data["session"] = session = create_campaign_session(campaign, categories)
        elif request.args.get("next", "false").lower() == "true":
            # iterating with test & update
            campaign = campaign_data["map"]
            if campaign.game_is_active():
                # end previous turn, this wipe whatever data is left
                campaign.end_turn()
                logger.debug("Running all 3 phases at once.")
                # TODO delegate specific running into
                campaign.full_phase_deploy()
                campaign.full_phase_move()
                campaign.full_phase_attack()
            else:
                logger.info("Game is finished; will only load the data.")
        else:
            # do nothing at the moment
            campaign = campaign_data["map"]
        # check appropriate phases; this should enable corresponding fields down in the website
        phase = campaign.current_phase 
        kwargs = {"polygons": campaign.retrieve_draw_map(), "arrows": campaign.retrieve_draw_arrows(), "phase": phase, "colorscheme": campaign.retrieve_player_color(), "player_names": campaign.retrieve_player_names(), "terrain_scheme": {t: (t[0].upper() + t[1:], TERRAIN_COLOR[t], TERRAIN_ICON[t]) for t in TERRAIN_COLOR}}
        if phase == "attack":
            # attack is in (source_province_name, target_province_name, source_id, target_id, max_attack_amount)
            kwargs["attacks"] = [(campaign.pname(s), campaign.pname(t), s, t, a) for s, t, a in campaign.all_attack_vectors(0)]
        elif phase == "moves":
            # move is in (source_province_name, source_id, [(target_province_name, target_id)..], move_amount)
            kwargs["moves"] = [(campaign.pname(s), s, [(campaign.pname(t), t) for t in ts], a) for a, s, ts in campaign.retrieve_all_movements(0)]
        elif phase == "deploy":
            logger.debug("Deploy phase; TODO show deployment result") 
        else:
            # should be the end phase, need no extra data 
            logger.debug("End phase; Next button should be enabled")

        # retrieve/generate the new quiz key; for now only allow 1 key for whole turn.
        orders = campaign_data["session"]["orders"]
        if len(orders) > 1:
            logger.warning("Campaign is having more than 1 quiz ready; check the cleanup function. Keys: {}".format(orders.keys()))
        current_key = next(iter(orders.keys()), None)
        if current_key is None:
            logger.info("No key-quiz currently exist; creating new.")
            result, current_key = build_order_quiz(campaign_data["session"])
            if not result:
                # failure for some reason; key cannot be generated.
                logger.error("Failure when generating key: {}".format(current_key))
                current_key = None 
        kwargs["quiz_key"] = current_key

        if(request.method == "GET"):
            if campaign.flavor_text:
                full_action_logs = list(campaign.flavor_text.get_full_logs(text_mode=False))
            # for get, return whole page to read
            return flask.render_template("campaign.html", full_action_logs=full_action_logs, **kwargs)
        else:
            if campaign.flavor_text and campaign.last_action_logs:
                # take & void the log after actions had been committed
                action_logs = campaign.last_action_logs 
                campaign.last_action_logs = []
            # for post, return jsonified data to update the map 
            return flask.jsonify(result=True, action_logs=action_logs, **kwargs)

    @app.route("/campaign_action", methods=["GET", "POST"])
    def campaign_action():
        # The player action will go through 3 steps
        # 1. submit the action to be used (POST here)
        # 2. see confirm_action
        # 3. reload the appropriate next action (GET here)
        if "map" not in campaign_data:
            return flask.jsonify(result=False, error="No campaign exist, request/submit action invalid.")
        campaign = campaign_data["map"]
        if request.method == "GET":
            # receiving all possible actions of player. Right now using player 0 
            if campaign.current_phase == "attack":
                attacks = [(campaign.pname(s), campaign.pname(t), s, t, a) for s, t, a in campaign.all_attack_vectors(0)]
                return flask.jsonify(result=True, attacks=attacks)
            elif campaign.current_phase == "moves":
                moves = [(campaign.pname(s), s, [(campaign.pname(t), t) for t in ts], a) for a, s, ts in campaign.retrieve_all_movements(0)]
                return flask.jsonify(result=True, moves=moves)
            elif campaign.current_phase == "deploy":
                raise NotImplementedError
            elif campaign.current_phase == "end":
                raise NotImplementedError
            else:
                return flask.jsonify(result=False, error="Unrecognized current_phase: {}".format(campaign.current_phase)) 
        else:
            # submitting the action coming from user 
            action_type, action_data = request.get_json()
            if action_type in ("attack", "moves", "deploy"):
                # TODO check appropriate phase in the campaign, and appropriate player; for now use 0
                campaign.update_action(0, action_type, action_data)
                return flask.jsonify(result=True)
            else:
                return flask.jsonify(result=False, error="Invalid action_type: {}".format(action_type))
 
    @app.route("/confirm_action", methods=["POST"])
    def confirm_action():
        # The player action will go through 3 steps
        # 1./3. see campaign_action
        # 2. confirm the action is correctly registered
        # TODO pops a random quiz through campaign's session on attack/defense 
        use_quiz = request.args.get("use_quiz", "false").lower() == "true"
        if use_quiz:
            raise NotImplementedError
        else:
            # just start the next appropriate phase accordingly 
            campaign = campaign_data.get("campaign", None)
            if campaign is None:
                return flask.jsonify(result=False, error="No campaign available")
            if campaign.current_phase == "deploy":
                logger.debug("Phase: executing deploy, -> moves")
                campaign.phase_deploy_reinforcement()
            elif campaign.current_phase == "moves":
                logger.debug("Phase: executing moves, -> attack")
                campaign.phase_perform_movement()
            elif campaign.current_phase == "attack":
                logger.debug("Phase: executing attack, end turn -> next")
                campaign.phase_perform_attack()
                campaign.end_turn()
            else:
                return flask.jsonify(result=False, error="Unrecognized phase: {}".format(campaign.current_phase))

    @app.route("/set_coef", methods=["GET"])
    def set_coef():
        # DEBUG: set the specific player_coef of the campaign for now. If this works, upgrade to trigger the quiz.
        campaign = campaign_data.get("map", None)
        if campaign is None:
            return flask.jsonify(result=False, error="No campaign available")
        coef = float(request.args.get("coef", 2.0))
        campaign.set_player_coef(coef)
        return flask.jsonify(result=True)
        

    @app.route("/campaign_quiz", methods=["GET"])
    def campaign_quiz():
        # allow access to the quiz in this link; this should have a secret agreed-upon key when confirm_action trigger 
        key = request.args.get("key", None)
        if key is None:
            return flask.jsonify(result=False, error="Invalid key for campaign_quiz")
        return access_order_quiz(campaign_data["session"], key)

    @app.route("/campaign_quiz_submit", methods=["POST"])
    def campaign_quiz_submit():
        """Same as session_routes's submit for the most part."""
        try:
            student_key  = request.args.get("key")
            submitted_answers = request.get_json()
            return submit_order_quiz_result(campaign_data["map"], campaign_data["session"], submitted_answers, student_key)
        except Exception as e:
            logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
            return flask.jsonify(result=False, error=str(e), error_traceback=traceback.format_exc())

    return campaign_data, app
