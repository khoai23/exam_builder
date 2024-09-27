"""Routes for accessing, monitoring or playing campaign. Also will settle accordingly with an exam trigger.
"""
import random, secrets, time
import flask
from flask import Flask, request, url_for
import traceback 

from src.campaign import * # clamp down later
from src.session import ExamManager 

import logging 
logger = logging.getLogger(__name__)

from typing import Optional, List, Tuple, Any, Union, Dict 


"""This is for a special campaign session. Instead of student id, this session object receives a specific player order and shuffle an appropriate quiz for that."""

def create_campaign_session(exam_manager, request):
    # first, create the campaign. TODO allow 
    # give 0 a superior bot 
    def PrioritizedBot(player_id, *args, **kwargs):
        if player_id == 1:
            logger.debug("Allegedly better bot for player 1")
            # combined variant between FrontlineBot & LandGrabBot; need tweaking for coef
            return SecureFrontlineBot(player_id, aspects=[TerrainAwarenessAspect(), ExplorerAspect()], debug=True, *args, **kwargs)
        elif player_id == 3:
            logger.debug("Balancer bot for player 3.")
            return FrontlineBot(player_id, aspects=[CoalitionAspect()], *args, **kwargs)
        else:
            logger.debug("Normal bot for player {:d}".format(player_id))
            return FrontlineBot(player_id, *args, **kwargs) 
    name_generator_cue = request.args.get("name_type", "gook").lower()
    name_generator_class = NAME_GENERATOR_BY_CUE[name_generator_cue]
    campaign = PlayerCampaign(players=[1], player_names=["Glorious Green", "Revolutionary Red", "Confidential Cyan", "Brash Beige"], colorscheme=["yellowgreen", "salmon", "powderblue", "moccasin"], bot_class=PrioritizedBot, name_generator=name_generator_class(shared_kwargs={"filter_generation_rule": True}), rules=[TerrainRule, CoreRule, ScorchedRule, RandomFactorRule, ExhaustionRule], flavor_text=FormattedFlavorText)
    # similarly, create a symbiotic session 
    # random of either 4, max-in-cache, or total category, depending on which is lowest
    quiz_data = exam_manager.quiz_data
    categories = random.sample(quiz_data.categories, k=min(4, len(quiz_data.categories), quiz_data._maximum_cached))
    logger.debug("Creating session with categories: {}".format(categories))
    
    return {"map": campaign, "categories": categories, "exam": dict()} 

_default_coefficient_calculator = lambda c, t: 0.5 + (2.0 * c / t) * 0.5 # worst at 0.5, break even (1.0) at 50%, and best at 1.5
def build_order_quiz(exam_manager, campaign_data: dict, quiz_count: int=10, duration_min: int=15, select_category: Optional[str]=None, coefficient_calculator: callable=_default_coefficient_calculator, convert_embedded_image: bool=True) -> Tuple[bool, str]:
    # attempt to build a quiz for the order, returning a referring key to be re-accessed if necessary 
    # get a random key
    key = secrets.token_hex(8)
    if select_category:
        # if there is a valid select_category, use that 
        if select_category not in campaign_data["categories"]:
            # invalid category, break out 
            return False, "Invalid category {} (possible: {})".format(select_category, campaign_data["categories"])
    else:
        # if not, select one of the category randomly
        select_category = random.choice(campaign_data["categories"])
    # with a valid category, generate appropriate quiz on range of that category
    # TODO deeper selection mode (e.g by tag)
    # TODO offload this selection into exam_manager
    available = exam_manager.quiz_data.load_category(select_category)
    if len(available) < quiz_count:
        # not enough question to load, throw a warning 
        logger.warning("Category \"{}\" only has {} question, while requiring {}. Trimming requirement.".format(select_category, len(available), quiz_count))
        quiz_count = len(available)
    question_ids = random.sample(range(len(available)), k=quiz_count)
    questions, correct = exam_manager.generate_quiz(select_category, [(len(question_ids), 0.0, question_ids)], convert_embedded_image=convert_embedded_image)
    # write it into the "orders" section 
    start_time = time.time()
    end_time = time.time() + duration_min * 60
    campaign_data["exam"][key] = {"category": select_category, "exam_data": questions, "correct": correct, "start_time": start_time, "end_time": end_time, "coefficient_calculator": coefficient_calculator}
    # return appropriate data to access
    return True, key

def access_order_quiz(campaign_data: dict, key: str):
    order_data = campaign_data["exam"][key]
    # calculate the remaining time
    start_time, end_time = order_data["start_time"], order_data["end_time"]
    exam_duration = end_time - start_time
    elapsed = min(time.time() - start_time, exam_duration)
    remaining = exam_duration - elapsed 
    exam_duration_min = int(exam_duration) // 60
    # convert the exam_data into image-compatible version
    exam_data = order_data["exam_data"]
    if(time.time() > end_time):
        # render the error when timer is exceeded
        return flask.render_template("error.html", error="Order quiz over; cannot submit", error_traceback=None)
    else:
        # render normally
        return flask.render_template("exam.html", student_name="Player 0", exam_data=exam_data, submitted=("answers" in order_data), elapsed=elapsed, remaining=remaining, exam_setting={"campaign_data_name": "Quiz campaign_data", "exam_duration": exam_duration_min}, custom_navbar=True, score=None, submit_route="campaign_quiz_submit")

def submit_order_quiz_result(campaign_data: dict, submitted_answers: Dict, key: str):
    # simplified variant of the order quiz; 
    campaign = campaign_data["map"]
    order_data = campaign_data["exam"][key]
    if("answers" in order_data):
        return flask.jsonify(result=False, error="Already have an submitted answer.")
    else:
        # record to the student info
        order_data["answers"] = submitted_answers 
        # extract the correct vs total; campaign_data will create appropriate coefficient by its function
        coefficient_calculator = order_data["coefficient_calculator"]
        correct = 0
        for sub, crt in zip(submitted_answers, order_data["correct"]):
            if sub == crt:
                correct += 1
        total = len(order_data["correct"])
        order_data["order_coef"] = order_coef = coefficient_calculator(correct, total)
        # use the localstorage to trigger update from the campaign map 
        # do not send it over through localstorage; since such data could be tampered with 
        campaign_data["exam"].pop(key) # TODO perform cleanups when end turn instead; allowing revisit to see the correct section
        # TODO allow exam bonus to last depending on how many questions attempted.
        campaign.set_player_coef(order_coef, duration=5)
        return flask.jsonify(result=True, correct=order_data["correct"], score=order_coef, coef=order_coef, trigger_campaign_update=True)



def build_game_routes(app: Flask, exam_manager: ExamManager, login_decorator: callable=lambda f: f) -> Tuple[Dict, Flask]:
    current_data = exam_manager._quiz_data
    # campaign management here 
    campaign_data = {}
    @app.route("/play", methods=["GET", "POST"])
    def play():
        if "map" not in campaign_data or request.args.get("redo", "false").lower() == "true":
            logger.debug("Create new campaign map")
            campaign_data.update(create_campaign_session(exam_manager, request))
            campaign = campaign_data["map"]
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
        orders = campaign_data["exam"]
        if len(orders) > 1:
            logger.warning("Campaign is having more than 1 quiz ready; check the cleanup function. Keys: {}".format(orders.keys()))
        current_key = next(iter(orders.keys()), None)
        if current_key is None:
            logger.info("No key-quiz currently exist; creating new.")
            result, current_key = build_order_quiz(exam_manager, campaign_data)
            if not result:
                # failure for some reason; key cannot be generated.
                logger.error("Failure when generating key: {}".format(current_key))
                current_key = None 
        kwargs["quiz_key"] = current_key

        if(request.method == "GET"):
            if campaign.flavor_text:
                full_action_logs = list(campaign.flavor_text.get_full_logs(text_mode=False))
            # for get, return whole page to read
            return flask.render_template("game/strategic.html", full_action_logs=full_action_logs, **kwargs)
        else:
            if campaign.flavor_text and campaign.last_action_logs:
                # take & void the log after actions had been committed
                action_logs = campaign.last_action_logs 
                campaign.last_action_logs = []
            else:
                action_logs = []
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
        duration = int(request.args.get("duration", 1))
        campaign.set_player_coef(coef, duration=duration)
        return flask.jsonify(result=True)
        

    @app.route("/campaign_quiz", methods=["GET"])
    def campaign_quiz():
        # allow access to the quiz in this link; this should have a secret agreed-upon key when confirm_action trigger 
        key = request.args.get("key", None)
        if key is None:
            return flask.jsonify(result=False, error="Invalid key for campaign_quiz")
        return access_order_quiz(campaign_data, key)

    @app.route("/campaign_quiz_submit", methods=["POST"])
    def campaign_quiz_submit():
        """Same as session_routes's submit for the most part."""
        try:
            student_key  = request.args.get("key")
            submitted_answers = request.get_json()
            return submit_order_quiz_result(campaign_data, submitted_answers, student_key)
        except Exception as e:
            logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
            return flask.jsonify(result=False, error=str(e), error_traceback=traceback.format_exc())

    @app.route("/scenario", methods=["GET"])
    def tactical_scenario():
        # Displaying a battalion level scenario that run automatically as-is.
        # get the hardcoded one for now
        scenario = HardcodedScenario()
        return flask.render_template("game/tactical.html", **scenario.convert_to_template_data())

    return campaign_data, app
