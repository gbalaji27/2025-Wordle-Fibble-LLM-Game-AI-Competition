"""
GameState - Complete Wordle/Fibble game with integrated AI solver
"""

import random
import re
from typing import List, Optional, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from classes.LetterCell import LetterCell, Feedback
from constants import LLM_MODEL, MAX_LLM_CONTINUOUS_CALLS


class Status(Enum):
    playing = "playing"
    end = "end"


class Word:
    """Represents a single guess with its letters and feedback"""
    def __init__(self):
        self.cells: List[LetterCell] = [LetterCell() for _ in range(5)]
        self.word: str = ""
    
    def set_word(self, word: str):
        self.word = word.lower()
        for i, letter in enumerate(word[:5]):
            self.cells[i].set_letter(letter)
    
    def set_feedback(self, feedback: List[Feedback]):
        for i, fb in enumerate(feedback):
            self.cells[i].set_feedback(fb)
    
    def get_feedback(self) -> List[Feedback]:
        return [cell.feedback for cell in self.cells]


# =============================================================================
# AI SOLVER - Integrated directly into this file
# =============================================================================

@dataclass
class Constraints:
    """Tracks all known constraints from guesses"""
    correct_pos: Dict[int, str] = field(default_factory=dict)
    excluded_pos: Dict[int, Set[str]] = field(default_factory=lambda: {i: set() for i in range(5)})
    min_count: Dict[str, int] = field(default_factory=dict)
    max_count: Dict[str, int] = field(default_factory=dict)
    
    def update(self, word: str, feedback: List[Feedback], ignore_column: int = -1):
        """Update constraints from a guess. For Fibble, ignore_column skips a lying column."""
        word = word.lower()
        confirmed = {}
        
        for i, (letter, fb) in enumerate(zip(word, feedback)):
            # Skip the lie column in Fibble mode
            if i == ignore_column:
                continue
                
            if fb == Feedback.correct:
                self.correct_pos[i] = letter
                confirmed[letter] = confirmed.get(letter, 0) + 1
            elif fb == Feedback.present:
                self.excluded_pos[i].add(letter)
                confirmed[letter] = confirmed.get(letter, 0) + 1
        
        for letter, count in confirmed.items():
            self.min_count[letter] = max(self.min_count.get(letter, 0), count)
        
        for i, (letter, fb) in enumerate(zip(word, feedback)):
            # Skip the lie column in Fibble mode
            if i == ignore_column:
                continue
                
            if fb == Feedback.incorrect:
                self.max_count[letter] = confirmed.get(letter, 0)
                if confirmed.get(letter, 0) == 0:
                    for j in range(5):
                        if j != ignore_column:  # Don't add exclusions based on lie column
                            self.excluded_pos[j].add(letter)
    
    def matches(self, word: str) -> bool:
        """Check if word satisfies all constraints"""
        word = word.lower()
        
        for pos, letter in self.correct_pos.items():
            if word[pos] != letter:
                return False
        
        for pos, excluded in self.excluded_pos.items():
            if word[pos] in excluded:
                return False
        
        counts = {}
        for c in word:
            counts[c] = counts.get(c, 0) + 1
        
        for letter, min_c in self.min_count.items():
            if counts.get(letter, 0) < min_c:
                return False
        
        for letter, max_c in self.max_count.items():
            if counts.get(letter, 0) > max_c:
                return False
        
        return True


# Optimal starting words (information-theoretic best)
STARTERS = ["salet", "reast", "crate", "trace", "slate", "crane", "slant"]

# Word list - common 5-letter English words
WORDS = {
    "aback", "abase", "abate", "abbey", "abbot", "abhor", "abide", "abort",
    "about", "above", "abuse", "abyss", "acorn", "acrid", "actor", "acute",
    "adage", "adapt", "admit", "adobe", "adopt", "adore", "adorn", "adult",
    "aegis", "after", "again", "agape", "agate", "agent", "agile", "aging",
    "agony", "agree", "ahead", "aisle", "alarm", "album", "alert", "algae",
    "alibi", "alien", "align", "alike", "alive", "allay", "alley", "allot",
    "allow", "alloy", "aloft", "alone", "along", "aloof", "aloud", "alpha",
    "altar", "alter", "amass", "amaze", "amber", "amble", "amend", "amiss",
    "among", "ample", "amuse", "angel", "anger", "angle", "angry", "angst",
    "anime", "ankle", "annex", "annoy", "antic", "anvil", "aorta", "apart",
    "aphid", "apple", "apply", "apron", "arbor", "ardor", "arena", "argue",
    "arise", "armor", "aroma", "arose", "array", "arrow", "arson", "artsy",
    "ascot", "ashen", "aside", "askew", "asset", "atlas", "atoll", "atone",
    "attic", "audio", "audit", "augur", "aunty", "avail", "avert", "avoid",
    "await", "awake", "award", "aware", "awful", "awoke", "axial", "axiom",
    "azure", "bacon", "badge", "badly", "bagel", "baggy", "baker", "balmy",
    "banal", "banjo", "barge", "baron", "basal", "basic", "basil", "basin",
    "basis", "batch", "bathe", "baton", "batty", "beach", "beady", "beard",
    "beast", "beech", "beefy", "began", "begin", "begun", "being", "belch",
    "belie", "belle", "belly", "below", "bench", "beret", "berry", "berth",
    "beset", "bevel", "bible", "bicep", "bight", "bilge", "binge", "bingo",
    "birch", "birth", "bison", "black", "blade", "blame", "bland", "blank",
    "blare", "blast", "blaze", "bleak", "bleat", "bleed", "blend", "bless",
    "blimp", "blind", "blink", "bliss", "blitz", "bloat", "block", "bloke",
    "blond", "blood", "bloom", "blown", "blues", "bluff", "blunt", "blurb",
    "blurt", "blush", "board", "boast", "bobby", "bongo", "bonus", "boost",
    "booth", "booty", "booze", "borax", "borne", "bosom", "bossy", "botch",
    "bough", "bound", "bowel", "boxer", "brace", "braid", "brain", "brake",
    "brand", "brash", "brass", "brave", "bravo", "brawl", "brawn", "bread",
    "break", "breed", "briar", "bribe", "brick", "bride", "brief", "brine",
    "bring", "brink", "brisk", "broad", "broil", "broke", "brood", "brook",
    "broom", "broth", "brown", "brunt", "brush", "brute", "buddy", "budge",
    "buggy", "bugle", "build", "built", "bulge", "bulky", "bully", "bunch",
    "bunny", "burly", "burnt", "burst", "bushy", "butch", "buyer", "bylaw",
    "cabal", "cabby", "cabin", "cable", "cacao", "cache", "cacti", "caddy",
    "cadet", "camel", "cameo", "canal", "candy", "canny", "canoe", "caper",
    "carat", "cargo", "carol", "carry", "carve", "caste", "catch", "cater",
    "catty", "caulk", "cause", "cease", "cedar", "cello", "chafe", "chaff",
    "chain", "chair", "chalk", "champ", "chant", "chaos", "chard", "charm",
    "chart", "chase", "chasm", "cheap", "cheat", "check", "cheek", "cheer",
    "chess", "chest", "chick", "chide", "chief", "child", "chili", "chill",
    "chimp", "china", "chirp", "choir", "choke", "chord", "chore", "chose",
    "chuck", "chump", "chunk", "churn", "chute", "cider", "cigar", "cinch",
    "circa", "civic", "civil", "clack", "claim", "clamp", "clang", "clank",
    "clash", "clasp", "class", "clean", "clear", "cleat", "cleft", "clerk",
    "click", "cliff", "climb", "cling", "cloak", "clock", "clone", "close",
    "cloth", "cloud", "clout", "clown", "clubs", "cluck", "clump", "clung",
    "coach", "coast", "cobra", "cocoa", "colon", "color", "comet", "comfy",
    "comic", "comma", "conch", "condo", "coral", "corny", "couch", "cough",
    "could", "count", "coupe", "court", "coven", "cover", "covet", "cower",
    "crack", "craft", "cramp", "crane", "crank", "crash", "crass", "crate",
    "crave", "crawl", "craze", "crazy", "creak", "cream", "credo", "creed",
    "creek", "creep", "creme", "crepe", "crept", "crest", "crick", "cried",
    "crime", "crimp", "crisp", "croak", "crock", "crone", "crony", "crook",
    "cross", "crowd", "crown", "crude", "cruel", "crush", "crust", "crypt",
    "cubic", "cumin", "cupid", "curly", "curry", "curse", "curve", "cyber",
    "cycle", "cynic", "daddy", "daily", "dairy", "daisy", "dance", "dandy",
    "datum", "dealt", "death", "debit", "debug", "debut", "decal", "decay",
    "decor", "decoy", "decry", "defer", "deity", "delay", "delta", "delve",
    "demon", "demur", "denim", "dense", "depot", "depth", "derby", "deter",
    "devil", "diary", "dicey", "digit", "dimly", "diner", "dingo", "dingy",
    "dirty", "disco", "ditch", "ditto", "ditty", "diver", "dizzy", "dodge",
    "dogma", "doing", "dolly", "donor", "donut", "doubt", "dough", "dowdy",
    "dowel", "dowry", "dozen", "draft", "drain", "drake", "drama", "drank",
    "drape", "drawl", "drawn", "dread", "dream", "dress", "dried", "drier",
    "drift", "drill", "drink", "drive", "droit", "droll", "drone", "drool",
    "droop", "dross", "drove", "drown", "drugs", "drunk", "dryer", "dryly",
    "duchy", "dully", "dummy", "dumpy", "dunce", "dusky", "dusty", "dutch",
    "dwarf", "dwell", "dying", "eager", "eagle", "early", "earth", "easel",
    "eaten", "eater", "ebony", "edict", "edify", "eerie", "eight", "eject",
    "elbow", "elder", "elect", "elegy", "elfin", "elite", "elope", "elude",
    "elves", "email", "embed", "ember", "empty", "enact", "endow", "enemy",
    "enjoy", "ennui", "ensue", "enter", "entry", "envoy", "epoch", "epoxy",
    "equal", "equip", "erase", "erect", "erode", "error", "erupt", "essay",
    "ether", "ethic", "ethos", "evade", "event", "every", "evict", "evoke",
    "exact", "exalt", "excel", "exert", "exile", "exist", "expat", "expel",
    "extol", "extra", "exude", "exult", "fable", "facet", "faint", "fairy",
    "faith", "false", "famed", "fancy", "fatal", "fatty", "fault", "fauna",
    "favor", "feast", "feign", "felon", "femur", "fence", "feral", "ferry",
    "fetal", "fetch", "fetid", "fetus", "fever", "fewer", "fiber", "fibre",
    "field", "fiend", "fiery", "fifth", "fifty", "fight", "filch", "filet",
    "filly", "filmy", "filth", "final", "finch", "first", "fishy", "fixed",
    "fixer", "fizzy", "fjord", "flack", "flail", "flair", "flake", "flaky",
    "flame", "flank", "flare", "flash", "flask", "fleck", "flesh", "flick",
    "flier", "fling", "flint", "flirt", "float", "flock", "flood", "floor",
    "floss", "flour", "flout", "flown", "fluff", "fluid", "fluke", "flung",
    "flunk", "flush", "flute", "foamy", "focal", "focus", "foggy", "foist",
    "folly", "foray", "force", "forge", "forgo", "forte", "forth", "forty",
    "forum", "found", "foyer", "frail", "frame", "frank", "fraud", "freak",
    "freed", "fresh", "friar", "fried", "frill", "frisk", "frizz", "frock",
    "frond", "front", "frost", "froth", "frown", "froze", "fruit", "fudge",
    "fugue", "fully", "fungi", "funky", "funny", "furor", "furry", "fussy",
    "fuzzy", "gaffe", "gaily", "gamer", "gamma", "gamut", "gassy", "gaudy",
    "gauge", "gaunt", "gauze", "gavel", "gawky", "gazer", "geeky", "geese",
    "genie", "genre", "ghost", "giant", "giddy", "girth", "giver", "gizmo",
    "glade", "gland", "glare", "glass", "glaze", "gleam", "glean", "glide",
    "glint", "gloat", "globe", "gloom", "glory", "gloss", "glove", "glyph",
    "gnash", "gnome", "godly", "going", "golly", "gonad", "goner", "gooey",
    "goofy", "goose", "gorge", "gouge", "gourd", "grace", "grade", "graft",
    "grail", "grain", "grand", "grant", "grape", "graph", "grasp", "grass",
    "grate", "grave", "gravy", "graze", "great", "greed", "green", "greet",
    "grief", "grill", "grime", "grimy", "grind", "gripe", "grits", "groan",
    "groin", "groom", "grope", "gross", "group", "grout", "grove", "growl",
    "grown", "gruel", "gruff", "grunt", "guano", "guard", "guava", "guess",
    "guest", "guide", "guild", "guilt", "guise", "gulch", "gummy", "guppy",
    "gusto", "gusty", "gypsy", "habit", "haiku", "hairy", "halve", "handy",
    "happy", "hardy", "harem", "harpy", "harry", "harsh", "haste", "hasty",
    "hatch", "hater", "haunt", "haven", "havoc", "hazel", "heady", "heard",
    "heart", "heath", "heave", "heavy", "hedge", "hefty", "heist", "hello",
    "hence", "heron", "hilly", "hinge", "hippo", "hippy", "hitch", "hoard",
    "hobby", "hoist", "holly", "homer", "honey", "honor", "horde", "horny",
    "horse", "hotel", "hotly", "hound", "house", "hovel", "hover", "howdy",
    "hubby", "human", "humid", "humor", "humus", "hunch", "hunky", "hurry",
    "husky", "hussy", "hyena", "hymen", "hyper", "icier", "icing", "ideal",
    "idiom", "idiot", "idler", "idyll", "igloo", "image", "imbue", "impel",
    "imply", "inane", "incur", "index", "indie", "inept", "inert", "infer",
    "ingot", "inlay", "inlet", "inner", "input", "inter", "intro", "ionic",
    "irate", "irony", "islet", "issue", "itchy", "ivory", "jaunt", "jazzy",
    "jeans", "jelly", "jenny", "jerky", "jewel", "jiffy", "jimmy", "joint",
    "joist", "joker", "jolly", "joust", "judge", "juice", "juicy", "jumbo",
    "jumpy", "junco", "junky", "juror", "karma", "kayak", "kebab", "khaki",
    "kinky", "kiosk", "kitty", "knack", "knead", "kneed", "kneel", "knelt",
    "knife", "knock", "knoll", "known", "koala", "krill", "label", "labor",
    "laden", "ladle", "lager", "lance", "lanky", "lapel", "lapse", "large",
    "larva", "lasso", "latch", "later", "latex", "lathe", "latte", "laugh",
    "layer", "leach", "leafy", "leaky", "leant", "leapt", "learn", "lease",
    "leash", "least", "leave", "ledge", "leech", "leery", "legal", "leggy",
    "lemon", "lemur", "leper", "level", "lever", "libel", "light", "liken",
    "lilac", "limbo", "limit", "lined", "linen", "liner", "lingo", "lipid",
    "liter", "lithe", "lived", "liven", "liver", "livid", "llama", "loamy",
    "loath", "lobby", "local", "locus", "lodge", "lofty", "logic", "login",
    "loins", "loner", "loopy", "loose", "lorry", "loser", "louse", "lousy",
    "loved", "lover", "lower", "lowly", "loyal", "lucid", "lucky", "lumen",
    "lumpy", "lunar", "lunch", "lunge", "lusty", "lying", "lymph", "lynch",
    "lyric", "macaw", "macho", "macro", "madam", "madly", "mafia", "magic",
    "magma", "maize", "major", "maker", "mambo", "mamma", "manga", "mange",
    "mango", "mangy", "mania", "manic", "manly", "manor", "maple", "march",
    "marry", "marsh", "mason", "match", "mater", "matey", "mauve", "maxim",
    "maybe", "mayor", "mealy", "meant", "meaty", "mecca", "medal", "media",
    "medic", "melee", "melon", "mercy", "merge", "merit", "merry", "messy",
    "metal", "meter", "metro", "micro", "midst", "might", "milky", "mimic",
    "mince", "mined", "miner", "minim", "minor", "minty", "minus", "mirth",
    "miser", "missy", "misty", "miter", "mixed", "mixer", "model", "modem",
    "mogul", "moist", "molar", "moldy", "money", "month", "mooch", "moody",
    "moose", "moped", "moral", "moron", "morph", "mossy", "motel", "motif",
    "motor", "motto", "moult", "mound", "mount", "mourn", "mouse", "mousy",
    "mouth", "moved", "mover", "movie", "mower", "mucky", "mucus", "muddy",
    "mulch", "mummy", "munch", "mural", "murky", "mushy", "music", "musky",
    "musty", "myrrh", "nadir", "naive", "named", "nanny", "nasal", "nasty",
    "natal", "naval", "navel", "needy", "neigh", "nerve", "nervy", "never",
    "newer", "newly", "nicer", "niche", "niece", "nifty", "night", "ninja",
    "ninny", "ninth", "nippy", "noble", "nobly", "noise", "noisy", "nomad",
    "noose", "north", "notch", "noted", "novel", "nudge", "nurse", "nutty",
    "nylon", "nymph", "oaken", "oasis", "occur", "ocean", "octet", "odder",
    "oddly", "offal", "offer", "often", "oiled", "olden", "older", "olive",
    "omega", "onion", "onset", "opera", "optic", "orbit", "order", "organ",
    "other", "otter", "ought", "ounce", "outdo", "outer", "outgo", "ovary",
    "overt", "owing", "owner", "oxide", "ozone", "paddy", "pagan", "paint",
    "panda", "panel", "panic", "pansy", "pants", "papal", "paper", "parka",
    "party", "pasta", "paste", "pasty", "patch", "patio", "patsy", "patty",
    "pause", "payee", "payer", "peace", "peach", "pearl", "pecan", "pedal",
    "penal", "penny", "perch", "peril", "perky", "pesky", "pesto", "petal",
    "petty", "phase", "phone", "phony", "photo", "piano", "picky", "piece",
    "piety", "piggy", "pilot", "pinch", "piney", "pinky", "pinto", "pious",
    "piper", "pitch", "pithy", "pivot", "pixel", "pixie", "pizza", "place",
    "plaid", "plain", "plane", "plank", "plant", "plate", "plaza", "plead",
    "pleas", "pleat", "plied", "plier", "plods", "pluck", "plumb", "plume",
    "plump", "plunk", "plush", "poach", "poems", "point", "poise", "poker",
    "polar", "polka", "polyp", "pooch", "poppy", "porch", "poser", "posit",
    "posse", "pouch", "pound", "power", "prank", "prawn", "preen", "press",
    "price", "prick", "pride", "pried", "prime", "primo", "print", "prior",
    "prism", "privy", "prize", "probe", "promo", "prone", "prong", "proof",
    "prose", "proud", "prove", "prowl", "proxy", "prude", "prune", "psalm",
    "pubic", "pudgy", "pulse", "punch", "pupil", "puppy", "puree", "purge",
    "purse", "pushy", "putty", "pygmy", "quack", "quaff", "quail", "qualm",
    "quark", "quart", "quasi", "queen", "query", "quest", "queue", "quick",
    "quiet", "quill", "quilt", "quirk", "quota", "quote", "rabbi", "rabid",
    "racer", "radar", "radii", "radio", "radon", "rainy", "raise", "rajah",
    "rally", "ranch", "randy", "range", "rapid", "raspy", "ratio", "ratty",
    "raven", "rayon", "razor", "reach", "react", "reads", "ready", "realm",
    "reams", "rebel", "rebut", "recap", "recur", "redux", "refer", "regal",
    "rehab", "reign", "relax", "relay", "relic", "remit", "remix", "renal",
    "renew", "repay", "repel", "reply", "rerun", "reset", "resin", "retch",
    "retro", "retry", "reuse", "revel", "rhino", "rhyme", "rider", "ridge",
    "rifle", "right", "rigid", "rigor", "rinse", "ripen", "risen", "riser",
    "risky", "ritzy", "rival", "river", "rivet", "roach", "roast", "robin",
    "robot", "rocks", "rocky", "rodeo", "roger", "rogue", "roomy", "roost",
    "rotor", "rouge", "rough", "round", "rouse", "route", "rowdy", "rowed",
    "rower", "royal", "ruddy", "ruder", "rugby", "ruins", "ruled", "ruler",
    "rules", "rumba", "rumor", "rupee", "rural", "rusty", "sadly", "safer",
    "saint", "saker", "salad", "salet", "sally", "salon", "salsa", "salty",
    "salve", "salvo", "saner", "sandy", "sappy", "sassy", "satin", "satyr",
    "sauce", "saucy", "sauna", "saute", "saved", "saver", "savor", "savoy",
    "savvy", "scald", "scale", "scalp", "scaly", "scamp", "scant", "scare",
    "scarf", "scary", "scene", "scent", "scion", "scoff", "scold", "scone",
    "scoop", "scope", "score", "scorn", "scour", "scout", "scowl", "scram",
    "scrap", "scree", "screw", "scrub", "seamy", "sedan", "seedy", "segue",
    "seize", "semen", "sense", "sepia", "serum", "serve", "setup", "seven",
    "sever", "sewer", "shack", "shade", "shady", "shaft", "shake", "shaky",
    "shall", "shame", "shank", "shape", "shard", "share", "shark", "sharp",
    "shave", "shawl", "shear", "sheen", "sheep", "sheer", "sheet", "shelf",
    "shell", "shift", "shine", "shiny", "ships", "shire", "shirk", "shirt",
    "shock", "shone", "shook", "shoot", "shops", "shore", "short", "shots",
    "shout", "shove", "shown", "shows", "showy", "shrew", "shrub", "shrug",
    "shuck", "shunt", "shush", "shyly", "siege", "sight", "sigma", "silky",
    "silly", "since", "sinew", "singe", "siren", "sissy", "sixth", "sixty",
    "sized", "sizer", "sizes", "skate", "skeet", "skein", "skier", "skies",
    "skiff", "skill", "skimp", "skirt", "skulk", "skull", "skunk", "slack",
    "slain", "slang", "slant", "slash", "slate", "slave", "sleek", "sleep",
    "sleet", "slept", "slice", "slick", "slide", "slime", "slimy", "sling",
    "slink", "slope", "slosh", "sloth", "slump", "slung", "slunk", "slurp",
    "slush", "slyly", "smack", "small", "smart", "smash", "smear", "smell",
    "smelt", "smile", "smirk", "smite", "smith", "smock", "smoke", "smoky",
    "snack", "snafu", "snail", "snake", "snaky", "snare", "snarl", "sneak",
    "sneer", "snide", "sniff", "snipe", "snoop", "snore", "snort", "snout",
    "snowy", "snuck", "snuff", "soapy", "sober", "solar", "solid", "solve",
    "sonar", "sonic", "sooth", "sooty", "sorry", "sorts", "sound", "south",
    "sowed", "sower", "space", "spade", "spank", "spare", "spark", "spasm",
    "spawn", "speak", "spear", "speck", "speed", "spell", "spend", "spent",
    "spice", "spicy", "spied", "spiel", "spike", "spill", "spine", "spiny",
    "spire", "spite", "splat", "split", "spoil", "spoke", "spoof", "spook",
    "spool", "spoon", "spore", "sport", "spots", "spout", "spray", "spree",
    "sprig", "spunk", "spurn", "spurt", "squad", "squat", "squid", "stack",
    "staff", "stage", "staid", "stain", "stair", "stake", "stale", "stalk",
    "stall", "stamp", "stand", "stank", "staph", "stare", "stark", "stars",
    "start", "stash", "state", "stave", "stays", "stead", "steak", "steal",
    "steam", "steel", "steep", "steer", "stein", "stems", "steps", "stern",
    "stews", "stick", "stiff", "still", "stilt", "sting", "stink", "stint",
    "stock", "stoic", "stoke", "stole", "stomp", "stone", "stony", "stood",
    "stool", "stoop", "stops", "store", "stork", "storm", "story", "stout",
    "stove", "strap", "straw", "stray", "strep", "strew", "strip", "strut",
    "stuck", "studs", "study", "stuff", "stump", "stung", "stunk", "stunt",
    "style", "suave", "sugar", "suite", "sulky", "sully", "sunny", "super",
    "surer", "surge", "surly", "sushi", "swami", "swamp", "swank", "swarm",
    "swash", "swath", "swear", "sweat", "sweep", "sweet", "swell", "swept",
    "swift", "swill", "swine", "swing", "swipe", "swirl", "swish", "swiss",
    "swoon", "swoop", "sword", "swore", "sworn", "swung", "tabby", "table",
    "taboo", "tacit", "tacky", "taffy", "taint", "taken", "taker", "tally",
    "talon", "tamed", "tamer", "tango", "tangy", "taper", "tapir", "tardy",
    "tarot", "taste", "tasty", "tatty", "taunt", "tawny", "teach", "teams",
    "teary", "tease", "teddy", "teems", "teens", "teeny", "teeth", "tempo",
    "tempt", "tends", "tenor", "tense", "tenth", "tents", "tepee", "tepid",
    "terms", "terra", "terse", "tests", "testy", "thank", "theft", "their",
    "theme", "there", "these", "thick", "thief", "thigh", "thing", "think",
    "third", "thong", "thorn", "those", "three", "threw", "throb", "throw",
    "thrum", "thuds", "thumb", "thump", "tiara", "tibia", "tidal", "tiger",
    "tight", "tilde", "timer", "timid", "tipsy", "titan", "title", "toast",
    "today", "toddy", "token", "tonal", "toned", "toner", "tongs", "tonic",
    "tools", "tooth", "topaz", "topic", "torch", "torso", "total", "totem",
    "touch", "tough", "tours", "towel", "tower", "towns", "toxic", "trace",
    "track", "tract", "trade", "trail", "train", "trait", "tramp", "trash",
    "trawl", "tread", "treat", "trees", "trend", "tress", "triad", "trial",
    "tribe", "trick", "tried", "trier", "tries", "trill", "trims", "tripe",
    "trite", "troll", "tromp", "troop", "trope", "troth", "trots", "trout",
    "trove", "truce", "truck", "truer", "truly", "trump", "trunk", "truss",
    "trust", "truth", "tryst", "tubal", "tubes", "tulip", "tumor", "tuned",
    "tuner", "tunic", "turbo", "turns", "tutor", "twain", "twang", "tweak",
    "tweed", "tweet", "twice", "twigs", "twill", "twine", "twins", "twirl",
    "twist", "tying", "udder", "ulcer", "ultra", "umbra", "uncle", "uncut",
    "under", "undid", "undue", "unfed", "unfit", "unify", "union", "unite",
    "units", "unity", "unlit", "unmet", "untie", "until", "unwed", "unzip",
    "upper", "upset", "urban", "urine", "usage", "usher", "using", "usual",
    "usurp", "utter", "vague", "valet", "valid", "valor", "value", "valve",
    "vapid", "vapor", "vault", "vaunt", "vegan", "veils", "venom", "venue",
    "verbs", "verge", "verse", "vicar", "video", "views", "vigil", "vigor",
    "villa", "vines", "vinyl", "viola", "viper", "viral", "virus", "visor",
    "vista", "vital", "vivid", "vixen", "vocal", "vodka", "vogue", "voice",
    "voila", "vomit", "voted", "voter", "vouch", "vowel", "vying", "wacky",
    "waded", "wader", "wafer", "waged", "wager", "wages", "wagon", "waist",
    "waive", "walks", "walls", "waltz", "wands", "wants", "warty", "waste",
    "watch", "water", "watts", "waved", "waver", "waves", "waxed", "waxen",
    "weary", "weave", "wedge", "weeds", "weedy", "weeks", "weigh", "weird",
    "wells", "welsh", "wench", "whack", "whale", "wharf", "wheat", "wheel",
    "whelp", "where", "which", "whiff", "while", "whims", "whine", "whiny",
    "whirl", "whisk", "white", "whole", "whoop", "whose", "widen", "wider",
    "widow", "width", "wield", "wills", "wince", "winch", "winds", "windy",
    "wines", "wings", "wiped", "wiper", "wired", "wires", "wiser", "wispy",
    "witch", "witty", "wives", "woken", "woman", "women", "woods", "woody",
    "woozy", "wordy", "works", "world", "worms", "worry", "worse", "worst",
    "worth", "would", "wound", "woven", "wrack", "wrath", "wreak", "wreck",
    "wrest", "wring", "wrist", "write", "wrong", "wrote", "wrung", "yacht",
    "yearn", "yeast", "yield", "young", "yours", "youth", "zebra", "zesty",
    "zonal", "zones", "reast", "tares", "rates", "stare", "tears", "aster",
    "earns", "nears",
}


def _call_llm(prompt: str) -> Optional[str]:
    """Call LLM API - supports Groq, Gemini, OpenRouter, Ollama (offline)"""
    import urllib.request
    import json
    import ssl
    import time
    
    # Determine which platform to use based on constants
    try:
        from constants import LLM_PLATFORM
    except ImportError:
        LLM_PLATFORM = "groq"
    
    # Only add delay for online APIs (not needed for local Ollama)
    if LLM_PLATFORM != "ollama":
        time.sleep(1.0)
    
    # Fix SSL certificate issue on macOS
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        if LLM_PLATFORM == "ollama":
            # LOCAL model - no API key, no rate limits!
            try:
                from constants import OLLAMA_HOST
            except ImportError:
                OLLAMA_HOST = "http://localhost:11434"
            
            url = f"{OLLAMA_HOST}/api/generate"
            headers = {"Content-Type": "application/json"}
            data = {
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 20}
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['response'].strip().lower()
        
        elif LLM_PLATFORM == "gemini":
            from constants import GEMINI_API_KEY
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 20}
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['candidates'][0]['content']['parts'][0]['text'].strip().lower()
        
        elif LLM_PLATFORM == "openrouter":
            from constants import OPENROUTER_API_KEY
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/wordle-solver",
                "X-Title": "Wordle Solver"
            }
            data = {
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 20
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content'].strip().lower()
        
        else:  # Default: Groq
            from constants import GROQ_API_KEY
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 10
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content'].strip().lower()
                
    except Exception as e:
        print(f"    [LLM Error: {e}]")
        return None


def _extract_word(text: str) -> Optional[str]:
    """Extract 5-letter word from response"""
    if not text:
        return None
    text = text.strip().lower()
    if len(text) == 5 and text.isalpha():
        return text
    words = re.findall(r'\b[a-zA-Z]{5}\b', text)
    for w in words:
        if w.lower() in WORDS:
            return w.lower()
    return words[0].lower() if words else None


def _score_word(word: str) -> float:
    """Score word by letter frequency"""
    freq = {'e': 12.7, 't': 9.1, 'a': 8.2, 'o': 7.5, 'i': 7.0, 'n': 6.7,
            's': 6.3, 'h': 6.1, 'r': 6.0, 'd': 4.3, 'l': 4.0, 'c': 2.8}
    return sum(freq.get(c, 0.1) for c in set(word)) + len(set(word)) * 2


# =============================================================================
# GAME STATE CLASS
# =============================================================================

class GameState:
    """Main game state for Wordle/Fibble"""
    
    # Class-level solver state (persists across guesses within a game)
    _constraints: Optional[Constraints] = None
    _candidates: List[str] = []
    _guess_num: int = 0
    _history: List[Tuple[str, List[Feedback]]] = []
    
    def __init__(self, show_window: bool = True, logging: bool = True):
        self.show_window = show_window
        self.logging = logging
        
        # Game configuration
        self.num_lies = 0
        self.num_guesses = 6
        
        # Game state
        self.words: List[Word] = []
        self.current_word_index = 0
        self.target_word = ""
        self.status = Status.playing
        self.success = False
        self.was_valid_guess = False
        
        # Word list for targets
        self.word_list = list(WORDS)
        
        # Fibble lie tracking
        self.lie_column = None
        self.lies_given = 0
        
        self.reset()
    
    def reset(self):
        """Reset game for a new round"""
        self.words = []
        self.current_word_index = 0
        self.target_word = random.choice(self.word_list)
        self.status = Status.playing
        self.success = False
        self.was_valid_guess = False
        
        # Fibble setup
        if self.num_lies > 0:
            self.lie_column = random.randint(0, 4)
            self.lies_given = 0
        else:
            self.lie_column = None
            self.lies_given = 0
        
        # Reset solver state
        GameState._constraints = Constraints()
        GameState._candidates = list(WORDS)
        GameState._guess_num = 0
        GameState._history = []
        
        if self.logging:
            print(f"New game. Target: {self.target_word}")
    
    def enter_word(self, guess: str):
        """Enter a guess and calculate feedback"""
        guess = guess.lower()
        
        word = Word()
        word.set_word(guess)
        
        feedback = self._calculate_feedback(guess)
        word.set_feedback(feedback)
        
        self.words.append(word)
        self.current_word_index = len(self.words)
        
        if guess == self.target_word:
            self.success = True
            self.status = Status.end
        elif len(self.words) >= self.num_guesses:
            self.success = False
            self.status = Status.end
        
        if self.logging:
            fb_str = ''.join(['🟩' if f == Feedback.correct else '🟨' if f == Feedback.present else '⬛' for f in feedback])
            print(f"  {guess.upper()} {fb_str}")
    
    def _calculate_feedback(self, guess: str) -> List[Feedback]:
        """Calculate feedback for a guess"""
        guess = guess.lower()
        target = self.target_word.lower()
        
        feedback = [Feedback.incorrect] * 5
        target_letters = list(target)
        
        # First pass: greens
        for i in range(5):
            if guess[i] == target[i]:
                feedback[i] = Feedback.correct
                target_letters[i] = None
        
        # Second pass: yellows
        for i in range(5):
            if feedback[i] == Feedback.incorrect:
                if guess[i] in target_letters:
                    feedback[i] = Feedback.present
                    target_letters[target_letters.index(guess[i])] = None
        
        # Fibble: apply lie
        if self.num_lies > 0 and self.lies_given < self.num_lies:
            feedback = self._apply_lie(feedback)
        
        return feedback
    
    def _apply_lie(self, feedback: List[Feedback]) -> List[Feedback]:
        """Apply lie for Fibble"""
        if self.lie_column is not None and self.lies_given < self.num_lies:
            col = self.lie_column
            if feedback[col] == Feedback.correct:
                feedback[col] = Feedback.incorrect
            elif feedback[col] == Feedback.present:
                feedback[col] = Feedback.incorrect
            else:
                feedback[col] = Feedback.present
            self.lies_given += 1
        return feedback
    
    def num_of_tries(self) -> int:
        """Return number of guesses made"""
        return len(self.words)
    
    def enter_word_from_ai(self) -> int:
        """
        Get word from AI solver and enter it.
        Returns: number of LLM calls made.
        """
        GameState._guess_num += 1
        
        # First guess: optimal starter
        if GameState._guess_num == 1:
            guess = STARTERS[0]
            self.enter_word(guess)
            self.was_valid_guess = True
            return 0
        
        # Get feedback from previous guess
        if self.words:
            prev = self.words[-1]
            word = prev.word.lower()
            feedback = prev.get_feedback()
            
            # Only update if not already processed
            if not GameState._history or GameState._history[-1][0] != word:
                if feedback and len(feedback) == 5:
                    # For Fibble: try to detect lie column
                    if self.num_lies > 0:
                        # Use conservative approach: apply constraints loosely
                        # Don't fully trust any single column's feedback
                        GameState._constraints.update(word, feedback)
                    else:
                        GameState._constraints.update(word, feedback)
                    GameState._history.append((word, feedback))
        
        # Filter candidates
        guessed_words = {w.word.lower() for w in self.words}
        GameState._candidates = [w for w in GameState._candidates 
                                  if GameState._constraints.matches(w) and w not in guessed_words]
        
        # For Fibble: if no candidates, try relaxing constraints
        if not GameState._candidates and self.num_lies > 0:
            # Try each column as potential lie column
            for lie_col in range(5):
                test_constraints = Constraints()
                for hist_word, hist_fb in GameState._history:
                    test_constraints.update(hist_word, hist_fb, ignore_column=lie_col)
                
                test_candidates = [w for w in WORDS 
                                   if test_constraints.matches(w) and w not in guessed_words]
                
                if test_candidates:
                    GameState._candidates = test_candidates
                    GameState._constraints = test_constraints
                    if self.logging:
                        print(f"    [Fibble: Suspecting lie in column {lie_col}]")
                    break
        
        # Single candidate - no LLM needed
        if len(GameState._candidates) == 1:
            guess = GameState._candidates[0]
            self.enter_word(guess)
            self.was_valid_guess = True
            return 0
        
        # No candidates - reset
        if not GameState._candidates:
            GameState._candidates = [w for w in WORDS 
                                      if GameState._constraints.matches(w)]
        
        # Still none - fallback
        if not GameState._candidates:
            guess = STARTERS[GameState._guess_num % len(STARTERS)]
            self.enter_word(guess)
            self.was_valid_guess = True
            return 0
        
        # Score and sort
        scored = sorted(GameState._candidates, key=_score_word, reverse=True)
        
        # Build detailed prompt like GPT-5 benchmark
        tries_left = self.num_guesses - len(self.words)
        
        prompt = "You are playing Wordle. Guess a 5-letter word.\n"
        
        # Fibble lie explanation
        if self.num_lies > 0:
            prompt += f"\nIMPORTANT: There are {self.num_lies} lies in feedback. "
            prompt += "Lies are ALWAYS in the SAME column for all guesses.\n"
        
        # Previous guesses and feedback
        if GameState._history:
            prompt += "\nPrevious guesses:\n"
            for word, feedback in GameState._history:
                fb_str = []
                for letter, fb in zip(word.upper(), feedback):
                    if fb == Feedback.correct:
                        fb_str.append(f"{letter}:GREEN")
                    elif fb == Feedback.present:
                        fb_str.append(f"{letter}:YELLOW")
                    else:
                        fb_str.append(f"{letter}:GRAY")
                prompt += f"  {word.upper()} -> {', '.join(fb_str)}\n"
        
        # Show candidates
        if len(scored) <= 15:
            prompt += f"\nValid words: {','.join(scored)}\n"
        else:
            prompt += f"\nTop candidates: {','.join(scored[:10])}\n"
        
        prompt += f"Tries left: {tries_left}\n"
        prompt += "Reply with ONLY a 5-letter word:"
        
        llm_calls = 0
        for attempt in range(MAX_LLM_CONTINUOUS_CALLS):
            resp = _call_llm(prompt)
            llm_calls += 1
            
            if resp:
                guess = _extract_word(resp)
                if guess and GameState._constraints.matches(guess):
                    self.enter_word(guess)
                    self.was_valid_guess = True
                    return llm_calls
                
                # Self-correction like GPT-5 benchmark
                if guess:
                    reasons = []
                    for i, letter in enumerate(guess):
                        if i in GameState._constraints.correct_pos:
                            if letter != GameState._constraints.correct_pos[i]:
                                reasons.append(f"Position {i+1} must be '{GameState._constraints.correct_pos[i].upper()}'")
                        if letter in GameState._constraints.excluded_pos.get(i, set()):
                            reasons.append(f"'{letter.upper()}' cannot be in position {i+1}")
                    
                    if reasons:
                        prompt += f"\n'{guess.upper()}' is invalid: {'; '.join(reasons[:3])}\nTry again:"
                    else:
                        prompt += f"\n'{guess.upper()}' not in word list. Pick from: {','.join(scored[:5])}\nTry again:"
        
        # Fallback
        guess = scored[0]
        self.enter_word(guess)
        self.was_valid_guess = True
        return llm_calls
