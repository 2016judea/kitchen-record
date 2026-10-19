"""The fix dictionary: each Priority-1 code the inspector keeps writing, in plain words.

Three fields per code, all 5th-grade English:
  plain   what the rule means
  checks  what the inspector physically does on the follow-up to see if it is fixed
  fix     what to do today so it passes

Written 2026-10-18 from the Minnesota Food Code (MN Rules 4626) text the city prints with
each violation, plus the city's page on how follow-ups work (minneapolismn.gov, "Health
inspection reports and dashboard", read 2026-10-18: follow-up within ~14 days, the
inspector "checks if violations have been corrected"). Codes not listed here fall back to
the city's own FoodCodeText for `plain` and generic checks/fix lines (see `lookup`).
"""

CODES = {
    "MN Rule 4626.0395A2": {
        "short": "Cold food too warm",
        "plain": "Food that needs to stay cold (meat, dairy, cut produce, cooked rice) has to be 41°F or colder in the fridge or cold line.",
        "checks": "Puts a probe thermometer into food in your coolers and on the cold line. Reads the cooler's own thermometer. Looks at how full the top of the prep cooler is.",
        "fix": "Put a thermometer in every cooler and check it twice a shift. Don't stack food above the fill line on the prep cooler. Keep lids on inserts. Get any cooler reading over 41°F serviced before the visit, and move its food to one that works.",
    },
    "MN Rule 4626.0040C": {
        "short": "No employee illness log",
        "plain": "You must keep a written log of when workers report being sick, and show it when asked.",
        "checks": "Asks the person in charge for the illness log and reads it. If there is no paper or binder to hand over, it is written up again.",
        "fix": "Print an employee illness log (the city and MDH both post a free one), put it in a binder by the office or time clock, and have every manager know where it is. Write today's date on the first line so it is not blank.",
    },
    "MN Rule 4626.0395A1": {
        "short": "Hot food too cool",
        "plain": "Food held hot (soup, rice, meat on the line, buffet) has to stay at 135°F or hotter.",
        "checks": "Probes food in your steam table, hot well, warmer or buffet and reads the number.",
        "fix": "Check hot-held food with a probe every two hours and write the number down. Turn the steam table on early so it is hot before food goes in. Reheat anything under 135°F to 165°F or throw it out.",
    },
    "MN Rule 4626.0805C1": {
        "short": "Bleach sanitizer too weak",
        "plain": "Your chlorine (bleach) sanitizer water has to test at 50 ppm or more, and be the right temperature.",
        "checks": "Dips a chlorine test strip in your sanitizer bucket and the dish sink's third compartment.",
        "fix": "Buy chlorine test strips and test every bucket when you mix it. Change buckets every two hours or when the water looks dirty. Post the mixing ratio by the sink.",
    },
    "MN Rule 4626.0405A": {
        "short": "Food kept past 7 days",
        "plain": "Cooked or opened cold food has to be thrown out seven days after it was made or opened. Day one is the day it was made.",
        "checks": "Opens your coolers and reads date labels on containers. Looks for anything with no date or a date more than 7 days old.",
        "fix": "Put a date label on every container the moment it is made or opened. Go through every cooler the night before and throw out anything past day 7 or with no label.",
    },
    "MN Rule 4626.0385A": {
        "short": "Cooling food too slowly",
        "plain": "Cooked food has to cool from 135°F to 70°F within two hours, and down to 41°F within six hours total.",
        "checks": "Probes food that was cooked earlier and is now cooling or in the cooler. Asks how you cool large batches and when they went in.",
        "fix": "Cool in shallow pans no more than 2 inches deep, uncovered, in the walk-in. Use an ice bath or ice paddle for soups and sauces. Write start time and temperature on the pan.",
    },
    "MN Rule 4626.1620": {
        "short": "Wrong sanitizer chemical",
        "plain": "Only approved sanitizers may touch surfaces that touch food. A cleaner is not a sanitizer.",
        "checks": "Reads the label on the sanitizer bottle or bucket and checks it is an EPA-registered food-contact sanitizer.",
        "fix": "Use only a labelled food-contact sanitizer (chlorine, quat or iodine) on prep tables and cutting boards. Keep the all-purpose cleaner for floors and walls, and store the two apart.",
    },
    "MN Rule 4626.0900": {
        "short": "Surfaces not sanitized",
        "plain": "Prep tables, boards, knives and slicers have to be sanitized after cleaning and before use, not just wiped.",
        "checks": "Watches staff clean a surface and asks what the second step is. Tests the sanitizer bucket.",
        "fix": "Train the two-step: wash, then sanitize and let it air dry. Keep a tested sanitizer bucket with a clean cloth at every prep station.",
    },
    "MN Rule 4626.0235A(1)": {
        "short": "Raw meat over ready-to-eat food",
        "plain": "Raw meat, poultry, fish and eggs have to be stored apart from food that will not be cooked again.",
        "checks": "Opens the walk-in and reach-ins and looks at what sits above what. Raw chicken on the shelf above lettuce is the classic write-up.",
        "fix": "Restack every cooler: ready-to-eat on top, then whole cuts, then ground meat, raw poultry on the bottom shelf. Put a shelf diagram on the walk-in door.",
    },
    "MN Rule 4626.0225A": {
        "short": "Bare hands on ready-to-eat food",
        "plain": "Food that will not be cooked again (salad, bread, garnish, sushi) may not be touched with bare hands.",
        "checks": "Watches the line and expo while plating. One bare-hand touch of a garnish is a write-up.",
        "fix": "Gloves, tongs, deli tissue or a scoop for anything that goes to the guest without cooking. Put a glove box at every station where plating happens.",
    },
    "MN Rule 4626.0805C3": {
        "short": "Quat sanitizer wrong strength",
        "plain": "Quaternary ammonium (quat) sanitizer has to be mixed to the strength on its label.",
        "checks": "Dips a quat test strip in your bucket and dish sink and compares the colour.",
        "fix": "Buy quat test strips for your brand. Test every bucket when it is mixed. If you use a wall dispenser, check its concentration weekly.",
    },
    "MN Rule 4626.0905B": {
        "short": "Dish machine not hot enough",
        "plain": "A hot-water dish machine has to get the dish surface to 160°F.",
        "checks": "Runs a rack with a thermolabel or max-register thermometer through your dish machine and reads it.",
        "fix": "Run a thermolabel through the machine each morning and keep the used labels. If it fails, call your dish-machine company before the visit.",
    },
    "MN Rule 4626.0040D": {
        "short": "No plan for a sick-guest report",
        "plain": "If a guest reports vomiting, diarrhea or a foodborne illness, the person in charge must report it to the health department.",
        "checks": "Asks the person in charge what they would do if a guest called in sick. The answer has to include calling the city.",
        "fix": "Post the Minneapolis Health Department number (612-673-2301) by the phone with one line: 'Guest reports illness: call this number.' Tell every manager.",
    },
    "MN Rule 4626.0075B-J": {
        "short": "Not washing hands between tasks",
        "plain": "Workers have to wash hands after the restroom, after touching raw meat, after touching their face or phone, and before putting on gloves.",
        "checks": "Watches the line for several minutes. Changing gloves without washing is the usual write-up.",
        "fix": "Hand sink stocked and clear at every station. Rule for the line: wash before new gloves, every time. Say it at pre-shift.",
    },
    "MN Rule 4626.1085A": {
        "short": "Missing backflow preventer",
        "plain": "Any hose or faucet that could pull dirty water back into the clean water line needs a backflow device.",
        "checks": "Looks at the mop sink faucet, hose bibs, the ice machine and soda lines for a backflow device.",
        "fix": "Screw a hose-bib vacuum breaker onto the mop sink faucet and any hose connection. If a line to a machine has none, a plumber fits one in under an hour.",
    },
    "MN Rule 4626.0235A(2)": {
        "short": "Raw meats mixed together",
        "plain": "Different raw meats have to be stored by cooking temperature: poultry below ground meat, ground meat below whole cuts.",
        "checks": "Looks at the order of raw meats on the cooler shelves.",
        "fix": "Bottom shelf chicken, then ground beef and pork, then whole steaks and fish. Label the shelves.",
    },
    "MN Rule 4626.0040A": {
        "short": "Staff not trained to report illness",
        "plain": "You must train staff to tell you when they have vomiting, diarrhea, jaundice, a sore throat with fever, or a diagnosed foodborne illness.",
        "checks": "Asks a worker what illnesses they have to report. Asks for your training record or signed agreement.",
        "fix": "Have every worker sign the MDH employee illness agreement form and keep the forms with the illness log.",
    },
    "MN Rule 4626.0845C": {
        "short": "Cutting boards not cleaned every 4 hours",
        "plain": "Boards, knives and slicers used with raw or cold food have to be cleaned and sanitized at least every four hours.",
        "checks": "Asks when the slicer or board was last cleaned and looks at it.",
        "fix": "Put a 4-hour clean on the line's task sheet: 10am, 2pm, 6pm. Clean the slicer between meats and at each mark.",
    },
    "MN Rule 4626.0500B": {
        "short": "Reusing single-use containers",
        "plain": "Single-use items (takeout tubs, grocery bags, sour cream pails) may not be reused to hold food.",
        "checks": "Looks for food stored in reused pails, grocery bags or takeout containers in coolers and dry storage.",
        "fix": "Move food into real food-grade containers with lids. Throw the reused pails out before the visit.",
    },
    "MN Rule 4626.0408B": {
        "short": "Time-as-control without marks",
        "plain": "If you hold food out at room temperature on time instead of temperature, it needs a written time mark and goes in the trash at 4 hours.",
        "checks": "Looks at food sitting out (rice, sushi rice, pizza, bread with butter) for a time label and asks for your written plan.",
        "fix": "Write a one-page time-control plan and label every pan with the discard time. Or put the food back on temperature control.",
    },
    "MN Rule 4626.0075A": {
        "short": "No hand wash before prep",
        "plain": "Workers must wash hands before they start handling food.",
        "checks": "Watches a worker come on shift or back from break and go to the line.",
        "fix": "Hand sink first, every time anyone steps onto the line. Put the sign on the kitchen door.",
    },
    "MN Rule 4626.0287A": {
        "short": "Gloves used for more than one task",
        "plain": "Gloves are for one task. Change them when you switch jobs, when they tear, or after touching anything that is not food.",
        "checks": "Watches a gloved worker move from raw to cooked, or touch a handle or phone and go back to food.",
        "fix": "Glove boxes at every station; the rule is new task, new gloves, with a hand wash in between.",
    },
    "MN Rule 4626.1040A": {
        "short": "Plumbing not to code",
        "plain": "Sinks, drains and water lines have to be installed to the plumbing code.",
        "checks": "Looks at the sink drains, the prep sink's air gap and any leaking or jury-rigged line.",
        "fix": "Have a licensed plumber fix the item named in the inspector's comment. Keep the invoice to show.",
    },
    "MN Rule 4626.0360A": {
        "short": "Reheating too low or too slow",
        "plain": "Cooked food that was chilled has to be reheated to 165°F within two hours before it goes on the hot line.",
        "checks": "Probes food that was just put in the steam table and asks how it was reheated.",
        "fix": "Reheat on the stove or in the oven, not in the steam table. Probe to 165°F before it goes in the well.",
    },
    "MN Rule 4626.1600": {
        "short": "Chemicals near food",
        "plain": "Cleaners and chemicals have to be stored away from food, dishes and linens.",
        "checks": "Looks under prep tables and on shelves for spray bottles and chemical jugs next to food or clean dishes.",
        "fix": "One chemical shelf, low and apart from food. Label every spray bottle.",
    },
    "MN Rule 4626.0270A": {
        "short": "Food on dirty surfaces",
        "plain": "Food may not touch equipment or surfaces that were not cleaned and sanitized.",
        "checks": "Looks at the slicer, can opener blade, ice scoop holder and prep surfaces for build-up.",
        "fix": "Break down and clean the slicer and can opener tonight. Add them to the closing checklist.",
    },
    "MN Rule 4626.0070A": {
        "short": "Hand washing too short",
        "plain": "Hands and lower arms have to be washed for 20 seconds with soap at a stocked hand sink.",
        "checks": "Watches a hand wash. Checks the hand sink for soap, towels and hot water.",
        "fix": "Soap and towels at every hand sink, every shift. Teach the 20 seconds at pre-shift.",
    },
    "MN Rule 4626.0250A": {
        "short": "Unapproved additive",
        "plain": "You may not add unapproved substances to food, or too much of an approved one (sulfites, nitrites, colour).",
        "checks": "Reads labels in dry storage and asks about anything named in the last report.",
        "fix": "Remove the item the inspector named. Keep the label of what replaced it.",
    },
    "MN Rule 4626.0130A": {
        "short": "Food from an unapproved source",
        "plain": "All food has to come from a licensed supplier, not a home kitchen or an unlicensed seller.",
        "checks": "Asks for the invoice for the item named and looks for home-made or unlabelled products.",
        "fix": "Buy from licensed suppliers and keep the invoices in a folder for the visit.",
    },
    "MN Rule 4626.0385B": {
        "short": "Room-temperature prep cooled too slowly",
        "plain": "Food made from room-temperature ingredients (tuna salad, cut melon) has to get to 41°F within four hours.",
        "checks": "Probes freshly made cold items and asks when they were made.",
        "fix": "Start with cold ingredients and cool in shallow pans. Date and time the pan.",
    },
    "MN Rule 4626.0905C": {
        "short": "Chemical sanitizer step skipped",
        "plain": "After washing, dishes and utensils have to be sanitized with an approved chemical at the right strength and time.",
        "checks": "Tests the third sink compartment or dish machine's sanitizer with a strip.",
        "fix": "Test strips at the dish sink. Fill the third compartment to the label strength every time.",
    },
    "MN Rule 4626.0260": {
        "short": "Ice used twice",
        "plain": "Ice that cooled bottles or packages may not be served to guests.",
        "checks": "Looks for bottles or cans buried in ice that is also used for drinks.",
        "fix": "Separate ice for drinks and ice for chilling. Label the wells.",
    },
    "MN Rule 4626.0320A": {
        "short": "Food uncovered",
        "plain": "Food on display has to be protected with lids, sneeze guards or packaging.",
        "checks": "Looks at the counter, buffet and pastry case for uncovered food within reach of guests.",
        "fix": "Sneeze guard or lids on anything displayed. Pastry case door closed.",
    },
}

GENERIC_CHECKS = "Looks for the exact thing written in the last report's comment and asks the person in charge what changed."
GENERIC_FIX = "Fix what the inspector's comment names, write down what you did and when, and have the person in charge able to show it on the visit."


def lookup(code: str, code_text: str | None) -> dict:
    """plain/checks/fix for a code; falls back to the city's own text."""
    c = CODES.get(code)
    if c:
        return {"short": c["short"], "plain": c["plain"], "checks": c["checks"], "fix": c["fix"], "hand_written": True}
    txt = (code_text or "").strip() or code
    short = txt.split(".")[0][:60]
    return {"short": short, "plain": txt, "checks": GENERIC_CHECKS, "fix": GENERIC_FIX, "hand_written": False}
