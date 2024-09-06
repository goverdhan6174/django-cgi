smtpcr = "\r\n"

smtpserver = {
    "ezweb.ne.jp": {
        "mx": 1,
        "max": 1,
        "1": "27.86.106.68",
        "2": "27.86.106.196",
        "per": 7,
        "thread": 25,
        "pwait": 200,
        "twait": 200,
        "swait": 2 * 60
    },
    "27.86.106.68": "mx01.au.com",
    "27.86.106.196": "mx02.au.com",
    "softbank.ne.jp": {
        "mx": 1,
        "max": 4,
        "1": "117.46.11.71",
        "2": "117.46.5.71",
        "3": "117.46.11.71",
        "4": "117.46.5.71",
        "per": 8,
        "thread": 140,
        "pwait": 150,
        "twait": 150,
        "swait": 2 * 60
    },
    "i.softbank.jp": {
        "mx": 1,
        "max": 4,
        "1": "117.46.9.104",
        "2": "117.46.7.40",
        "3": "117.46.9.104",
        "4": "117.46.7.40",
        "per": 7,
        "thread": 180,
        "pwait": 130,
        "twait": 130,
        "swait": 2 * 60
    },
    "docomo.ne.jp": {
        "mx": 4,
        "max": 4,
        "1": "203.138.180.112",
        "2": "203.138.181.240",
        "3": "203.138.181.112",
        "4": "203.138.180.240",
        "per": 5,
        "thread": 4,
        "pwait": 500,
        "twait": 3 * 60 * 1000,
        "swait": 15 * 60
    },
    "disney.ne.jp": {
        "mx": 1,
        "max": 2,
        "1": "117.46.7.41",
        "2": "117.46.5.73",
        "per": 8,
        "thread": 30,
        "pwait": 200,
        "twait": 200,
        "swait": 2 * 60
    },
    "ymobile.ne.jp": {
        "mx": 1,
        "max": 4,
        "1": "117.46.9.107",
        "2": "117.46.11.75",
        "3": "117.46.5.75",
        "4": "117.46.7.43",
        "per": 8,
        "thread": 140,
        "pwait": 150,
        "twait": 150,
        "swait": 2 * 60
    },
    "gmail.com": {
        "mx": 1,
        "max": 5,
        "1": "74.125.140.27",
        "2": "64.233.163.27",
        "3": "74.125.200.27",
        "4": "64.233.188.27",
        "5": "74.125.28.26",
        "per": 8,
        "thread": 18,
        "pwait": 200,
        "twait": 200,
        "swait": 2 * 60
    }
}

smtpsuffix = {
    "ezweb.ne.jp": "ezweb.ne.jp",
    "softbank.ne.jp": "softbank.ne.jp",
    "i.softbank.jp": "i.softbank.jp",
    "docomo.ne.jp": "docomo.ne.jp",
    "disney.ne.jp": "disney.ne.jp",
    "ymobile.ne.jp": "ymobile.ne.jp",
    "gmail.com": "gmail.com"
}
