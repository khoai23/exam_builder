"""Routes for accessing, monitoring or playing campaign. Also will settle accordingly with an exam trigger.
"""
import random
import flask
from flask import Flask, request, url_for
import traceback 

from src.campaign.default import CampaignMap, RussianNameGenerator, PolishNameGenerator, LandGrabBot, FrontlineBot 
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
                    # attack with enough forces, penalized with every move more
                    # still not good enough, the bot will still stream its maximum units forward. Should use another bot altogether
                    kwargs["certainty_coef"] = lambda a, d: -99.0 if a <= d else 5.0 if a < d + 3 else (5.0 - (a-d)*0.25)
                    # try attacking great gain target if available 
                    kwargs["return_coef"] = 1.0
                    # attack anything 
                    kwargs["unowned_coef"] = 0.0
                    # limit the attack to necessary only
                    kwargs["limit_attack_force"] = True
                    return LandGrabBot(player_id, *args, **kwargs)
                elif player_id == 3:
                    print("Different bot for player 3")
                    return FrontlineBot(player_id, *args, **kwargs)
                else:
                    print("Normal bot for player {:d}".format(player_id))
                    return LandGrabBot(player_id, *args, **kwargs)
            campaign_data["map"] = campaign = CampaignMap(bot_class=PrioritizedBot, name_generator=PolishNameGenerator(shared_kwargs={"filter_generation_rule": True}))
            # similarly, create a symbiotic session 
            # random 4 category 
            categories = random.sample(current_data.categories, k=4)
            print("Creating session with categories: {}".format(categories))
            campaign_data["session"] = session = create_campaign_session(campaign, categories)
        elif request.args.get("next", "false") == "true":
            # iterating with test & update
            campaign = campaign_data["map"]
            # end previous turn, this wipe whatever data is left
            campaign.end_turn()
            print("Iterating test.")
            campaign.test_start_phase()
            campaign.test_random_occupy(targetting_hostile=False)
        else:
            # do nothing at the moment
            campaign = campaign_data["map"]
        polygons = campaign.retrieve_draw_map()
        arrows = campaign.retrieve_draw_arrows()
        # print(polygons)
        # print(arrows)
        if(request.method == "GET"):
            # for get, return whole page
            return flask.render_template("campaign.html", polygons=polygons, arrows=arrows)
        else:
            # for post, return jsonified data 
            return flask.jsonify(result=True, polygons=polygons, arrows=arrows)

    @app.route("/campaign_action", methods=["POST"])
    def submit_action():
        # submitting the action coming from user 
        action_type, action_data = request.get_json()
        if "map" not in campaign_data:
            return flask.jsonify(result=False, error="No campaign exist, action invalid.")
        if action_type in ("attack", "move"):
            # TODO check appropriate phase in the campaign, and appropriate player; for now use 0
            campaign = campaign_data["map"]
            campaign.update_action(0, action_type, action_data)
            return flask.jsonify(result=True)
        else:
            return flask.jsonify(result=False, error="Invalid action_type: {}".format(action_type))
        
    @app.route("/")


    return campaign_data, app
