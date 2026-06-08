"""Ignatian Examen and Examination of Conscience templates.

These are static prayer scaffolds the frontend renders as guided forms.
Keeping them server-side lets us evolve the wording without app updates.
"""
from __future__ import annotations

EXAMEN_PROMPTS = [
    {
        "key": "gratitude",
        "title": "Gratitude",
        "prompt": "For what am I most grateful today?",
        "icon": "flower-outline",
    },
    {
        "key": "petition",
        "title": "Petition",
        "prompt": "Lord, give me light to see how Your Spirit moved today.",
        "icon": "sunny-outline",
    },
    {
        "key": "review",
        "title": "Review",
        "prompt": "Where did I notice God's presence today? In whom, in what?",
        "icon": "eye-outline",
    },
    {
        "key": "forgiveness",
        "title": "Forgiveness",
        "prompt": "Where did I fall short? What do I bring to His mercy?",
        "icon": "water-outline",
    },
    {
        "key": "renewal",
        "title": "Renewal",
        "prompt": "How will I respond tomorrow with greater love?",
        "icon": "sparkles-outline",
    },
]

EXAMINATION_SECTIONS = [
    {
        "key": "first",
        "title": "1st Commandment — Love of God",
        "prompts": [
            "Have I made anything more important than God — work, comfort, image, another person?",
            "Have I neglected daily prayer or the sacraments?",
            "Have I taken part in superstition, the occult, or false worship?",
            "Have I doubted or denied the faith publicly?",
        ],
    },
    {
        "key": "second",
        "title": "2nd Commandment — The Holy Name",
        "prompts": [
            "Have I used God's name in anger or carelessly?",
            "Have I broken a vow or solemn promise?",
            "Have I spoken irreverently of holy things, the saints, or the Blessed Mother?",
        ],
    },
    {
        "key": "third",
        "title": "3rd Commandment — The Lord's Day",
        "prompts": [
            "Have I missed Sunday Mass or a Holy Day of Obligation through my own fault?",
            "Have I done unnecessary servile work or treated Sunday as ordinary?",
            "Have I been late, distracted, or irreverent at Mass?",
        ],
    },
    {
        "key": "fourth",
        "title": "4th Commandment — Honor Parents and Authority",
        "prompts": [
            "Have I been disrespectful or unkind to my parents, spouse, employer, or those in authority?",
            "Have I neglected my duties to those in my care?",
            "Have I failed to bring my children up in the faith?",
        ],
    },
    {
        "key": "fifth",
        "title": "5th Commandment — Reverence for Life",
        "prompts": [
            "Have I harbored anger, hatred, or grudges?",
            "Have I harmed myself or others, in word, deed, or omission?",
            "Have I cooperated in or supported abortion, euthanasia, or violence?",
            "Have I abused alcohol, drugs, food, or sleep — or neglected proper care of my body?",
        ],
    },
    {
        "key": "sixth_ninth",
        "title": "6th & 9th Commandments — Chastity",
        "prompts": [
            "Have I entertained impure thoughts or desires willingly?",
            "Have I looked at pornography or impure media?",
            "Have I committed impure acts alone or with another?",
            "Have I been unfaithful to my spouse in mind, heart, or body?",
        ],
    },
    {
        "key": "seventh_tenth",
        "title": "7th & 10th Commandments — Justice",
        "prompts": [
            "Have I stolen, cheated, or taken what is not mine?",
            "Have I damaged property, cut corners at work, or wasted resources?",
            "Have I been greedy, envious, or unwilling to share with those in need?",
            "Have I paid my debts and made restitution where I owed it?",
        ],
    },
    {
        "key": "eighth",
        "title": "8th Commandment — Truthfulness",
        "prompts": [
            "Have I lied, exaggerated, or deceived?",
            "Have I gossiped, slandered, or damaged another's reputation?",
            "Have I broken a confidence or judged uncharitably?",
        ],
    },
    {
        "key": "precepts",
        "title": "Precepts of the Church",
        "prompts": [
            "Have I observed the days of fasting and abstinence?",
            "Have I gone to confession at least once a year, and received the Eucharist during the Easter season?",
            "Have I supported the Church and the work of evangelization?",
        ],
    },
]
