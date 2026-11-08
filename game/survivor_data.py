
# The Last Convoy
# Survivor name data

MALE_FIRST_NAMES = [
    "Aaron", "Adam", "Adrian", "Alan", "Albert",
    "Alex", "Alexander", "Andrew", "Anthony", "Arthur",
    "Austin", "Benjamin", "Blake", "Brandon", "Brian",
    "Bruce", "Caleb", "Carl", "Charles", "Christian",
    "Christopher", "Cody", "Connor", "Craig", "Daniel",
    "David", "Derek", "Dominic", "Donald", "Douglas",
    "Dylan", "Edward", "Eli", "Elijah", "Eric",
    "Ethan", "Eugene", "Evan", "Frank", "Gabriel",
    "Gary", "George", "Gerald", "Gordon", "Grant",
    "Gregory", "Harold", "Harry", "Henry", "Howard",
    "Hunter", "Ian", "Isaac", "Jack", "Jacob",
    "James", "Jason", "Jeffrey", "Jeremy", "Jesse",
    "Joel", "John", "Jonathan", "Jordan", "Jose",
    "Joseph", "Joshua", "Julian", "Justin", "Keith",
    "Kenneth", "Kevin", "Kyle", "Lawrence", "Leo",
    "Leonard", "Liam", "Logan", "Louis", "Lucas",
    "Luke", "Marcus", "Mark", "Martin", "Mason",
    "Matthew", "Michael", "Nathan", "Nathaniel", "Nicholas",
    "Noah", "Oliver", "Oscar", "Owen", "Patrick",
    "Paul", "Peter", "Philip", "Raymond", "Richard",
    "Robert", "Roger", "Ronald", "Russell", "Ryan",
    "Samuel", "Scott", "Sean", "Sebastian", "Stephen",
    "Steven", "Theodore", "Thomas", "Timothy", "Travis",
    "Trevor", "Tyler", "Victor", "Vincent", "Walter",
    "Wesley", "William", "Zachary"
]

FEMALE_FIRST_NAMES = [
    "Abigail", "Alexandra", "Alice", "Alicia", "Allison",
    "Amanda", "Amber", "Amy", "Andrea", "Angela",
    "Anna", "Annabelle", "April", "Ariana", "Ashley",
    "Audrey", "Autumn", "Ava", "Barbara", "Bethany",
    "Brianna", "Brooke", "Caitlin", "Caroline", "Catherine",
    "Charlotte", "Chelsea", "Chloe", "Christina", "Claire",
    "Clara", "Courtney", "Crystal", "Daisy", "Danielle",
    "Diana", "Donna", "Eleanor", "Elizabeth", "Ella",
    "Ellie", "Emily", "Emma", "Erica", "Erin",
    "Evelyn", "Faith", "Fiona", "Gabriella", "Grace",
    "Hailey", "Hannah", "Harper", "Heather", "Helen",
    "Isabella", "Jade", "Jamie", "Jane", "Jasmine",
    "Jennifer", "Jessica", "Jill", "Joanna", "Jordan",
    "Josephine", "Julia", "Julie", "Katherine", "Kathleen",
    "Kayla", "Kelly", "Kimberly", "Laura", "Lauren",
    "Leah", "Lillian", "Lily", "Lindsay", "Lisa",
    "Lucy", "Madeline", "Madison", "Margaret", "Maria",
    "Marie", "Mary", "Megan", "Melanie", "Michelle",
    "Morgan", "Naomi", "Natalie", "Nicole", "Nina",
    "Olivia", "Paige", "Patricia", "Rachel", "Rebecca",
    "Riley", "Rose", "Samantha", "Sandra", "Sarah",
    "Savannah", "Sharon", "Sierra", "Sophia", "Stephanie",
    "Susan", "Taylor", "Teresa", "Vanessa", "Victoria",
    "Violet", "Wendy", "Whitney", "Zoe"
]

LAST_NAMES = [
    "Adams", "Allen", "Anderson", "Armstrong", "Bailey",
    "Baker", "Barnes", "Bennett", "Brooks", "Brown",
    "Bryant", "Butler", "Campbell", "Carter", "Clark",
    "Collins", "Cook", "Cooper", "Cox", "Crawford",
    "Davis", "Diaz", "Edwards", "Ellis", "Evans",
    "Fisher", "Flores", "Foster", "Garcia", "Gibson",
    "Gonzalez", "Gordon", "Graham", "Gray", "Green",
    "Griffin", "Hall", "Hamilton", "Harris", "Hayes",
    "Henderson", "Hernandez", "Hill", "Howard", "Hughes",
    "Jackson", "James", "Jenkins", "Johnson", "Jones",
    "Kelly", "Kennedy", "King", "Lee", "Lewis",
    "Long", "Lopez", "Martin", "Martinez", "Miller",
    "Mitchell", "Moore", "Morgan", "Morris", "Murphy",
    "Nelson", "Parker", "Patterson", "Perez", "Perry",
    "Peterson", "Phillips", "Powell", "Price", "Ramirez",
    "Reed", "Richardson", "Rivera", "Roberts", "Robinson",
    "Rodriguez", "Rogers", "Ross", "Russell", "Sanchez",
    "Sanders", "Scott", "Simmons", "Smith", "Stewart",
    "Taylor", "Thomas", "Thompson", "Torres", "Turner",
    "Walker", "Ward", "Washington", "Watson", "White",
    "Williams", "Wilson", "Wood", "Wright", "Young"
]

# Special survivors: fixed identities (name, gender, age), never random.
# Add new entries here; the key is used to request them.
SPECIAL_SURVIVORS = {
    "donald_trump": {
        "first_name": "Donald",
        "last_name": "Trump",
        "gender": "Male",
        "age": 80,
    },
    "elon_musk": {
        "first_name": "Elon",
        "last_name": "Musk",
        "gender": "Male",
        "age": 55,
    },
    "rick_grimes": {
        "first_name": "Rick",
        "last_name": "Grimes",
        "gender": "Male",
        "age": 38,
    },

    # The Walking Dead
    "daryl_dixon": {
        "first_name": "Daryl",
        "last_name": "Dixon",
        "gender": "Male",
        "age": 40,
    },
    "michonne_hawthorne": {
        "first_name": "Michonne",
        "last_name": "Hawthorne",
        "gender": "Female",
        "age": 38,
    },
    "carol_peletier": {
        "first_name": "Carol",
        "last_name": "Peletier",
        "gender": "Female",
        "age": 45,
    },
    "glenn_rhee": {
        "first_name": "Glenn",
        "last_name": "Rhee",
        "gender": "Male",
        "age": 30,
    },
    "maggie_greene": {
        "first_name": "Maggie",
        "last_name": "Greene",
        "gender": "Female",
        "age": 30,
    },
    "negan_smith": {
        "first_name": "Negan",
        "last_name": "Smith",
        "gender": "Male",
        "age": 50,
    },
    "carl_grimes": {
        "first_name": "Carl",
        "last_name": "Grimes",
        "gender": "Male",
        "age": 13,
    },

    # The Last of Us
    "joel_miller": {
        "first_name": "Joel",
        "last_name": "Miller",
        "gender": "Male",
        "age": 50,
    },
    "ellie_williams": {
        "first_name": "Ellie",
        "last_name": "Williams",
        "gender": "Female",
        "age": 14,
    },
    "sarah_miller": {
        "first_name": "Sarah",
        "last_name": "Miller",
        "gender": "Female",
        "age": 12,
    },

    # Resident Evil
    "leon_kennedy": {
        "first_name": "Leon",
        "last_name": "Kennedy",
        "gender": "Male",
        "age": 27,
    },
    "claire_redfield": {
        "first_name": "Claire",
        "last_name": "Redfield",
        "gender": "Female",
        "age": 19,
    },
    "grace_ashcroft": {
        "first_name": "Grace",
        "last_name": "Ashcroft",
        "gender": "Female",
        "age": 28,
    },
    "ashley_graham": {
        "first_name": "Ashley",
        "last_name": "Graham",
        "gender": "Female",
        "age": 20,
    },
    "jill_valentine": {
        "first_name": "Jill",
        "last_name": "Valentine",
        "gender": "Female",
        "age": 23,
    },
    "chris_redfield": {
        "first_name": "Chris",
        "last_name": "Redfield",
        "gender": "Male",
        "age": 25,
    },
    "rebecca_chambers": {
        "first_name": "Rebecca",
        "last_name": "Chambers",
        "gender": "Female",
        "age": 18,
    },
    "sherry_birkin": {
        "first_name": "Sherry",
        "last_name": "Birkin",
        "gender": "Female",
        "age": 12,
    },
    "ada_wong": {
        "first_name": "Ada",
        "last_name": "Wong",
        "gender": "Female",
        "age": 30,
    },
    "carlos_oliveira": {
        "first_name": "Carlos",
        "last_name": "Oliveira",
        "gender": "Male",
        "age": 21,
    },

    # Shaun of the Dead
    "shaun_riley": {
        "first_name": "Shaun",
        "last_name": "Riley",
        "gender": "Male",
        "age": 29,
    },

    # Zombieland (names split phonetically from the city codenames)
    "tallahassee": {
        "first_name": "Tala",
        "last_name": "Hassee",
        "gender": "Male",
        "age": 45,
    },
    "columbus": {
        "first_name": "Colum",
        "last_name": "Bus",
        "gender": "Male",
        "age": 22,
    },
    "wichita": {
        "first_name": "Wichi",
        "last_name": "Taw",
        "gender": "Female",
        "age": 25,
    },
    "little_rock": {
        "first_name": "Little",
        "last_name": "Rock",
        "gender": "Female",
        "age": 12,
    },

    # Dead Rising
    "frank_west": {
        "first_name": "Frank",
        "last_name": "West",
        "gender": "Male",
        "age": 35,
    },
    "chuck_greene": {
        "first_name": "Chuck",
        "last_name": "Greene",
        "gender": "Male",
        "age": 30,
    },
    "katey_greene": {
        "first_name": "Katey",
        "last_name": "Greene",
        "gender": "Female",
        "age": 7,
    },
    "nick_ramos": {
        "first_name": "Nick",
        "last_name": "Ramos",
        "gender": "Male",
        "age": 24,
    },

    # World War Z (movie and book)
    "gerry_lane": {
        "first_name": "Gerry",
        "last_name": "Lane",
        "gender": "Male",
        "age": 42,
    },
    "karin_lane": {
        "first_name": "Karin",
        "last_name": "Lane",
        "gender": "Female",
        "age": 38,
    },
    "rachel_lane": {
        "first_name": "Rachel",
        "last_name": "Lane",
        "gender": "Female",
        "age": 11,
    },
    "constance_lane": {
        "first_name": "Constance",
        "last_name": "Lane",
        "gender": "Female",
        "age": 6,
    },
    "sean_collins": {
        "first_name": "Sean",
        "last_name": "Collins",
        "gender": "Male",
        "age": 42,
    },

    # Dying Light
    "kyle_crane": {
        "first_name": "Kyle",
        "last_name": "Crane",
        "gender": "Male",
        "age": 35,
    },
    "jade_aldemir": {
        "first_name": "Jade",
        "last_name": "Aldemir",
        "gender": "Female",
        "age": 28,
    },
    "rahim_aldemir": {
        "first_name": "Rahim",
        "last_name": "Aldemir",
        "gender": "Male",
        "age": 25,
    },
    "harris_brecken": {
        "first_name": "Harris",
        "last_name": "Brecken",
        "gender": "Male",
        "age": 50,
    },
    "imran_zere": {
        "first_name": "Imran",
        "last_name": "Zere",
        "gender": "Male",
        "age": 45,
    },
    "allen_camden": {
        "first_name": "Allen",
        "last_name": "Camden",
        "gender": "Male",
        "age": 40,
    },
    "amir_ghoreyshi": {
        "first_name": "Amir",
        "last_name": "Ghoreyshi",
        "gender": "Male",
        "age": 30,
    },

    # The Walking Dead (Telltale video game)
    "lee_everett": {
        "first_name": "Lee",
        "last_name": "Everett",
        "gender": "Male",
        "age": 37,
    },
    "clementine": {
        "first_name": "Clementine",
        "last_name": "Everett",
        "gender": "Female",
        "age": 8,
    },
    "kenny_russell": {
        "first_name": "Kenny",
        "last_name": "Telltale",
        "gender": "Male",
        "age": 55,
    },
    "katjaa_russell": {
        "first_name": "Katjaa",
        "last_name": "Telltale",
        "gender": "Female",
        "age": 35,
    },
    "duck_russell": {
        "first_name": "Duck",
        "last_name": "Telltale",
        "gender": "Male",
        "age": 10,
    },
    "lilly_caul": {
        "first_name": "Lilly",
        "last_name": "Caul",
        "gender": "Female",
        "age": 30,
    },
    "larry_caul": {
        "first_name": "Larry",
        "last_name": "Caul",
        "gender": "Male",
        "age": 55,
    },
    "ben_paul": {
        "first_name": "Ben",
        "last_name": "Paul",
        "gender": "Male",
        "age": 22,
    },
    "hershel_greene": {
        "first_name": "Hershel",
        "last_name": "Greene",
        "gender": "Male",
        "age": 60,
    },

    # Warm Bodies
    "romeo_grigio": {
        "first_name": "Romeo",
        "last_name": "Grigio",
        "gender": "Male",
        "age": 22,
    },
    "julie_grigio": {
        "first_name": "Julie",
        "last_name": "Grigio",
        "gender": "Female",
        "age": 19,
    },
    "perry_kelvin": {
        "first_name": "Perry",
        "last_name": "Kelvin",
        "gender": "Male",
        "age": 20,
    },
    "nora_greene": {
        "first_name": "Nora",
        "last_name": "Greene",
        "gender": "Female",
        "age": 19,
    },
    "marcus_corddry": {
        "first_name": "Marcus",
        "last_name": "Corddry",
        "gender": "Male",
        "age": 35,
    },
    "colonel_grigio": {
        "first_name": "Colonel",
        "last_name": "Grigio",
        "gender": "Male",
        "age": 55,
    },

    # I Am Legend
    "robert_neville": {
        "first_name": "Robert",
        "last_name": "Neville",
        "gender": "Male",
        "age": 40,
    },
    "anna_legend": {
        "first_name": "Anna",
        "last_name": "Montez",
        "gender": "Female",
        "age": 30,
    },
    "ethan_legend": {
        "first_name": "Ethan",
        "last_name": "Montez",
        "gender": "Male",
        "age": 9,
    },
}


# Special series: characters from the same series can be added together
# as a "special family". Members must be keys of SPECIAL_SURVIVORS.
# Real-life special survivors (no series) are not listed here.
SPECIAL_SERIES = {
    "the_walking_dead": {
        "name": "The Walking Dead",
        "members": [
            "rick_grimes", "carl_grimes", "daryl_dixon",
            "michonne_hawthorne", "carol_peletier", "glenn_rhee",
            "maggie_greene", "negan_smith",
        ],
    },
    "the_walking_dead_telltale": {
        "name": "The Walking Dead (Telltale)",
        "members": [
            "lee_everett", "clementine", "kenny_russell",
            "katjaa_russell", "duck_russell", "lilly_caul",
            "larry_caul", "ben_paul", "hershel_greene", "glenn_rhee",
        ],
    },
    "the_last_of_us": {
        "name": "The Last of Us",
        "members": ["joel_miller", "sarah_miller", "ellie_williams"],
    },
    "resident_evil": {
        "name": "Resident Evil",
        "members": [
            "leon_kennedy", "claire_redfield", "grace_ashcroft",
            "ashley_graham", "jill_valentine", "chris_redfield",
            "rebecca_chambers", "sherry_birkin", "ada_wong",
            "carlos_oliveira",
        ],
    },
    "shaun_of_the_dead": {
        "name": "Shaun of the Dead",
        "members": ["shaun_riley"],
    },
    "zombieland": {
        "name": "Zombieland",
        "members": [
            "tallahassee", "columbus", "wichita", "little_rock",
        ],
    },
    "dead_rising": {
        "name": "Dead Rising",
        "members": [
            "frank_west", "chuck_greene", "katey_greene", "nick_ramos",
        ],
    },
    "world_war_z": {
        "name": "World War Z",
        "members": [
            "gerry_lane", "karin_lane", "rachel_lane",
            "constance_lane", "sean_collins",
        ],
    },
    "dying_light": {
        "name": "Dying Light",
        "members": [
            "kyle_crane", "jade_aldemir", "rahim_aldemir",
            "harris_brecken", "imran_zere", "allen_camden",
            "amir_ghoreyshi",
        ],
    },
    "warm_bodies": {
        "name": "Warm Bodies",
        "members": [
            "romeo_grigio", "julie_grigio", "perry_kelvin",
            "nora_greene", "marcus_corddry", "colonel_grigio",
        ],
    },
    "i_am_legend": {
        "name": "I Am Legend",
        "members": ["robert_neville", "anna_legend", "ethan_legend"],
    },
}
