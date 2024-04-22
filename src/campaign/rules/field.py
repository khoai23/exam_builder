"""Rules that specifically affect provinces."""
import random

from src.campaign.rules.base_campaign import Rule 

class ScorchedRule(Rule):
    """Adding a "scorched" parameter into each province. In every turn, if a battle occurred in that province, scorched + 2; if not, scorched -1. Province with this parameter receives defensive bonus & lose values accordingly."""
    def __init__(self, campaign, scorched_defensive_bonus: float=0.05, scorched_value_penalty: float=0.4):
        super(ScorchedRule, self).__init__(campaign)
        self.def_bonus = scorched_defensive_bonus
        self.val_pen = scorched_value_penalty
        for *_, p in self.campaign._map:
            # record the scorched value & the original score to allow update per province changed.
            p["scorched"] = 0
            p["true_score"] = p["score"]

    def end_phase(self):
        for *_, p in self.campaign._map:
            # scorched is clamped into
            scorched = p["scorched"] = max(0, p["scorched"] - 1)
            p["score"] = max(p["true_score"] - int(self.val_pen * scorched), 1)

    def after_attack(self, player_id, full_result):
        # TODO don't cause scorching when taking neutral province
        result, province, casualty = full_result 
        if result:
            province["scorched"] = min(province["scorched"] + 3, 10) # this should result in +2 normally. Will cause hotly contested province to go into deep end, but eh. 

    def affect_attack(self, attack_modifier: float, defend_modifier: float, preserve_modifier: float, # affected modifiers
            attack_strength: int, defend_strength: int, attacker_id: int, defender_id: int, target_province_id: int): # additional info 
        new_defend_modifier = defend_modifier + (self.campaign._map[target_province_id][-1]["scorched"] * self.def_bonus)
        return attack_modifier, new_defend_modifier, preserve_modifier

    def modify_draw_map(self, draw_map):
        for *_, p in draw_map:
            if p["scorched"] >= 5:
                p["symbol"] = "({}\u2278)".format(p["scorched"]) + p.get("symbol", "")

TERRAIN = ["urban", "plain", "wood", "hill", "desert", "jagged"]
TERRAIN_BONUSES = { # only have defensive coef & preserve (occupy) penalty for now
    "urban":  (0.0, 4.0), # no defense boost, very heavy occupy penalty, presenting easy-to-take but hard-to-hold
    "wood":   (0.1, 2.0), # easier to defend, but a bit harder to occupy. Should make into natural defensive line
    "jagged": (0.08, 1.6), # a little bit less than woods in defensiveness, but still quite hard to occupy
    "hill":   (0.3, 1.2), # much easier to defend, but it's easier for enemy to roll past
    "plain":  (-0.1, 1.2), # minor defense & base occupy penalty to make them more attractive
    "desert": (-0.3, 1.0), # very hard to defend, very easy to roll past, balanced out by relatively worthless price 
}
TERRAIN_ICON = {
    "urban": "\u25A6",
    "wood": "\u23C5",
    "jagged": "\u2301",
    "hill": "\u25B3",
    "plain": "\u268D",
    "desert": "\u268A"
}
TERRAIN_COLOR = {
    "urban": "gold",
    "wood": "olivedrab",
    "jagged": "saddlebrown",
    "hill": "#0000AA20",
    "plain": "lightgrey",
    "desert": "sandybrown"
}
class TerrainRule(Rule):
    """Adding terrain to the map; which confers different bonuses & penalties. For now, hardcoding them."""
    def __init__(self, campaign):
        super(TerrainRule, self).__init__(campaign)
        for *_, p in self.campaign._map:
            if p["score"] >= 9:
                # enforce to be urban 
                p["terrain"] = "urban"
            elif p["score"] <= 2:
                # enforce to be desert 
                p["terrain"] = "desert"
            else:
                # to be the rest 
                p["terrain"] = random.choice(TERRAIN)
    
    def affect_attack(self, attack_modifier: float, defend_modifier: float, preserve_modifier: float, # affected modifiers
            attack_strength: int, defend_strength: int, attacker_id: int, defender_id: int, target_province_id: int): # additional info 
        terrain_type = self.campaign._map[target_province_id][-1]["terrain"]
        def_bonus, prsv_penalty = TERRAIN_BONUSES[terrain_type]
        new_defend_modifier = defend_modifier + def_bonus
        new_preserve_modifier = prsv_penalty # override directly
        return attack_modifier, new_defend_modifier, new_preserve_modifier 

    def modify_draw_map(self, draw_map):
        for *_, p in draw_map:
            p["symbol"] = TERRAIN_ICON[p["terrain"]] + p.get("symbol", "")
            p["bg"] = TERRAIN_COLOR[p["terrain"]]
            #p["border_size"] = 4
