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
            print("Create new campaign map")
            # give 0 a superior bot 
            def PrioritizedBot(player_id, *args, **kwargs):
                if player_id == 0:
                    print("Allegedly better bot for player 0")
                    # combined variant between FrontlineBot & LandGrabBot; need tweaking for coef
                    return OpportunistBot(player_id, grab_vs_security_coef=0.2, *args, **kwargs)
                elif player_id == 3:
                    print("Rogue bot for player 3.")
                    return FrontlineBot(player_id, *args, **kwargs)
                else:
                    print("Normal bot for player {:d}".format(player_id))
                    return FrontlineBot(player_id, aspects=[CoalitionAspect()], debug=True, *args, **kwargs) 
            name_generator_cue = request.args.get("name_type", "gook").lower()
            name_generator_class = NAME_GENERATOR_BY_CUE[name_generator_cue]
            campaign_data["map"] = campaign = BaseCampaign(players=[], bot_class=PrioritizedBot, name_generator=name_generator_class(shared_kwargs={"filter_generation_rule": True}), rules=[TerrainRule, ScorchedRule])
            # similarly, create a symbiotic session 
            # random 4 category 
            categories = random.sample(current_data.categories, k=min(4, len(current_data.categories)))
            print("Creating session with categories: {}".format(categories))
            campaign_data["session"] = session = create_campaign_session(campaign, categories)
        elif request.args.get("next", "false") == "true":
            # iterating with test & update
            campaign = campaign_data["map"]
            # end previous turn, this wipe whatever data is left
            campaign.end_turn()
            print("Running all 3 phases at once.")
            # TODO delegate specific running into
            campaign.full_phase_deploy()
            campaign.full_phase_move()
            campaign.full_phase_attack()
        else:
            # do nothing at the moment
            campaign = campaign_data["map"]
        # check appropriate phases; this should enable corresponding fields down in the website
        phase = campaign.current_phase 
        kwargs = {"polygons": campaign.retrieve_draw_map(), "arrows": campaign.retrieve_draw_arrows(), "phase": phase, "colorscheme": campaign.retrieve_player_color()}
        if phase == "attack":
            # attack is in (source_province_name, target_province_name, source_id, target_id, max_attack_amount)
            kwargs["attacks"] = [(campaign.pname(s), campaign.pname(t), s, t, a) for s, t, a in campaign.all_attack_vectors(0)]
        elif phase == "moves":
            # move is in (source_province_name, source_id, [(target_province_name, target_id)..], move_amount)
            kwargs["moves"] = [(campaign.pname(s), s, [(campaign.pname(t), t) for t in ts], a) for a, s, ts in campaign.retrieve_all_movements(0)]
        elif phase == "deploy":
            print("Deploy phase; TODO show deployment result") 
        else:
            # should be the end phase, need no extra data 
            print("End phase; Next button should be enabled")
        if(request.method == "GET"):
            # for get, return whole page to read
            return flask.render_template("campaign.html", **kwargs)
        else:
            # for post, return jsonified data to update the map 
            return flask.jsonify(result=True, **kwargs)

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
                print("Phase: executing deploy, -> moves")
                campaign.phase_deploy_reinforcement()
            elif campaign.current_phase == "moves":
                print("Phase: executing moves, -> attack")
                campaign.phase_perform_movement()
            elif campaign.current_phase == "attack":
                print("Phase: executing attack, end turn -> next")
                campaign.phase_perform_attack()
                campaign.end_turn()
            else:
                return flask.jsonify(result=False, error="Unrecognized phase: {}".format(campaign.current_phase))


    return campaign_data, app
