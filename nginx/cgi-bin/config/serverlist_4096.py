smtpcr = "\r\n"

smtpserver = {
    "ezweb.ne.jp": {
        "mx": 1,
        "max": 2,
        1: "27.86.106.68",
        2: "27.86.106.196",
        "per": 5,
        "thread": 20,
        "pwait": 200,
        "twait": 200,
        "swait": 2 * 60
    },
    "27.86.106.68": "mx01.au.com",
    "27.86.106.196": "mx02.au.com",
    "softbank.ne.jp": {
        "mx": 1,
        "max": 4,
        1: "117.46.11.71",
        2: "117.46.7.39",
        3: "117.46.5.71",
        4: "117.46.9.103",
        "per": 8,
        "thread": 220,
        "pwait": 150,
        "twait": 150,
        "swait": 2 * 60
    },
    "i.softbank.jp": {
        "mx": 1,
        "max": 4,
        1: "117.46.5.72",
        2: "117.46.9.104",
        3: "117.46.7.40",
        4: "117.46.11.72",
        "per": 50,
        "thread": 300,
        "pwait": 60,
        "twait": 60,
        "swait": 2 * 60
    },
    "docomo.ne.jp": {
        "mx": 4,
        "max": 4,
        1: "203.138.180.112",
        2: "203.138.181.240",
        3: "203.138.181.112",
        4: "203.138.180.240",
        "per": 5,
        "thread": 20,
        "pwait": 500,
        "twait": 3 * 60 * 1000,
        "swait": 15 * 60
    },
    "disney.ne.jp": {
        "mx": 1,
        "max": 4,
        1: "117.46.7.41",
        2: "117.46.9.105",
        3: "117.46.5.73",
        4: "117.46.11.73",
        "per": 8,
        "thread": 230,
        "pwait": 120,
        "twait": 120,
        "swait": 2 * 60
    },
    "ymobile.ne.jp": {
        "mx": 1,
        "max": 4,
        1: "117.46.11.75",
        2: "117.46.5.75",
        3: "117.46.7.43",
        4: "117.46.9.107",
        "per": 8,
        "thread": 230,
        "pwait": 120,
        "twait": 120,
        "swait": 2 * 60
    },
    "gmail.com": {
        "mx": 1,
        "max": 5,
        1: "142.250.101.27",
        2: "64.233.171.26",
        3: "142.250.152.27",
        4: "172.253.113.27",
        5: "173.194.77.27",
        # Uncomment the following lines if needed
        # 1: "74.125.143.26",
        # 2: "74.125.30.27",
        # 3: "74.125.28.26",
        # 4: "74.125.23.26",
        # 5: "74.125.200.27",
        "per": 8,
        "thread": 18,
        "pwait": 200,
        "twait": 200,
        "swait": 2 * 60
    },
    "rakuten.jp": {
        "mx": 1,
        "max": 8,
        1: "203.216.5.80",
        2: "203.216.5.83",
        3: "203.216.5.82",
        4: "203.216.5.81",
        5: "203.216.5.84",
        6: "203.216.5.85",
        7: "203.216.5.88",
        8: "203.216.5.89",
        "per": 8,
        "thread": 20,
        "pwait": 200,
        "twait": 200,
        "swait": 2 * 60
    },
    "mineo.jp": {
        "mx": 1,
        "max": 1,
        1: "202.238.198.39",
        "per": 7,
        "thread": 1,
        "pwait": 500,
        "twait": 3 * 60 * 1000,
        "swait": 15 * 60
    }
}

smtpsuffix = {
    "ezweb.ne.jp": "ezweb.ne.jp",
    "softbank.ne.jp": "softbank.ne.jp",
    "i.softbank.jp": "i.softbank.jp",
    "docomo.ne.jp": "docomo.ne.jp",
    "disney.ne.jp": "disney.ne.jp",
    "ymobile.ne.jp": "ymobile.ne.jp",
    "gmail.com": "gmail.com",
    "rakuten.jp": "rakuten.jp",
    "mineo.jp": "mineo.jp"
}
