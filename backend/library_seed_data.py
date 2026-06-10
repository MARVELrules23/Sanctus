"""Sanctus Library — seed data for public-domain spiritual classics.

Each book has one or more chapters with real public-domain text.
Long works only get a few "featured" chapters embedded; the
`source_url` lets users continue reading the full work in-app
via WebView. Modern apologists / copyrighted works are added as
`external` type — link only.

Chapter content is markdown; line breaks render as paragraphs.
Keep this file maintainable; admins can add more chapters via
`/api/library/admin/books/{book_id}/chapters` at runtime.
"""

from typing import List, Dict, Any


# Each entry shape:
#   {
#     slug, title, author, year, blurb, tradition (catholic-classic | doctor | mystic | apologist),
#     cover_color, cover_icon,
#     type: "embedded" | "external",
#     source_url: full-text URL (CCEL/Gutenberg/newadvent),
#     chapters: [{title, body_md}],
#   }


SEED_BOOKS: List[Dict[str, Any]] = [
    # ---------- Practice of the Presence of God ----------
    {
        "slug": "practice-presence-of-god",
        "title": "The Practice of the Presence of God",
        "author": "Brother Lawrence of the Resurrection",
        "year": 1692,
        "blurb": "Conversations and letters from a humble Carmelite kitchen brother whose constant awareness of God amid daily chores shaped Catholic spirituality for centuries.",
        "tradition": "mystic",
        "cover_color": "#7C3AED",
        "cover_icon": "flame-outline",
        "type": "embedded",
        "source_url": "https://www.ccel.org/ccel/lawrence/practice.html",
        "chapters": [
            {
                "title": "First Conversation",
                "body_md": (
                    "The first time I saw Brother Lawrence was upon the 3rd of August, 1666. "
                    "He told me that God had done him a singular favor in his conversion at the age of eighteen. "
                    "That in the winter, seeing a tree stripped of its leaves, and considering that within a little time the leaves would be renewed, and after that the flowers and fruit appear, he received a high view of the providence and power of God, which has never since been effaced from his soul.\n\n"
                    "That this view had perfectly set him loose from the world, and kindled in him such a love for God, that he could not tell whether it had increased in above forty years that he had lived since.\n\n"
                    "That he had been formerly a footman to M. Fieubert, the treasurer, and that he was a great awkward fellow who broke everything. That he had desired to be received into a monastery, thinking he would there be made to smart for his awkwardness and the faults he would commit, and so he should sacrifice to God his life, with its pleasures; but that God had disappointed him, he having met with nothing but satisfaction in that state.\n\n"
                    "That we should establish ourselves in a sense of God's presence, by continually conversing with Him. That it was a shameful thing to quit His conversation to think of trifles and fooleries."
                ),
            },
            {
                "title": "Second Conversation",
                "body_md": (
                    "He told me that all consists in one hearty renunciation of everything which we are sensible does not lead to God; that we might accustom ourselves to a continual conversation with Him, with freedom and in simplicity.\n\n"
                    "That we need only to recognize God intimately present with us, to address ourselves to Him every moment, that we may beg His assistance for knowing His will in things doubtful, and for rightly performing those which we plainly see He requires of us, offering them to Him before we do them, and giving Him thanks when we have done.\n\n"
                    "That in this conversation with God, we are also employed in praising, adoring, and loving Him incessantly, for His infinite goodness and perfection.\n\n"
                    "That, without being discouraged on account of our sins, we should pray for His grace with a perfect confidence, as relying upon the infinite merits of our Lord.\n\n"
                    "That God never failed offering us His grace at each action; that he distinctly perceived it, and never failed of it, unless when his thoughts had wandered from a sense of God's presence, or he had forgotten to ask His assistance."
                ),
            },
            {
                "title": "Fourth Letter",
                "body_md": (
                    "I have taken this opportunity to communicate to you the sentiments of one of our society concerning the admirable effects and continual assistances which he receives from the presence of God. Let you and me both profit by them.\n\n"
                    "You must know his continual care has been, for about forty years past that he has spent in religion, to be always with God; and to do nothing, say nothing, and think nothing which may displease Him; and this without any other view than purely for the love of Him, and because He deserves infinitely more.\n\n"
                    "He is now so accustomed to that Divine presence, that he receives from it continual succors upon all occasions. For about thirty years past, his soul has been filled with joys so continual, and sometimes so great, that he is forced to use means to moderate them, and to hinder their appearing outwardly.\n\n"
                    "If sometimes he is a little too much absent from that Divine presence, God presently makes Himself to be felt in his soul to recall him, which often happens when he is most engaged in his outward business."
                ),
            },
        ],
    },

    # ---------- Imitation of Christ ----------
    {
        "slug": "imitation-of-christ",
        "title": "The Imitation of Christ",
        "author": "Thomas à Kempis",
        "year": 1418,
        "blurb": "After the Bible itself, the most widely read Catholic devotional book in history. Direct, fatherly counsel for any soul seeking to know Christ.",
        "tradition": "catholic-classic",
        "cover_color": "#B45309",
        "cover_icon": "book-outline",
        "type": "embedded",
        "source_url": "https://www.ccel.org/ccel/kempis/imitation.html",
        "chapters": [
            {
                "title": "Book I, Ch. 1 — Imitation of Christ",
                "body_md": (
                    '"He that followeth Me, walketh not in darkness," saith the Lord (John 8:12). These are the words of Christ, by which we are taught how we ought to imitate His life and manners, if we will be truly enlightened, and be delivered from all blindness of heart.\n\n'
                    "Let therefore our chief endeavor be, to meditate upon the life of Jesus Christ.\n\n"
                    "The doctrine of Christ exceedeth all the doctrines of holy men; and he that hath the Spirit will find therein a hidden manna.\n\n"
                    "But it falleth out that many, although they often hear the gospel of Christ, are yet but little affected, because they have not the Spirit of Christ.\n\n"
                    "Whoever would fully and feelingly understand the words of Christ, must endeavor to conform his whole life to that of Christ.\n\n"
                    "What will it avail thee to dispute profoundly of the Trinity, if thou be void of humility, and art thereby displeasing to the Trinity?\n\n"
                    "Surely great words do not make a man holy and just; but a virtuous life maketh him dear to God."
                ),
            },
            {
                "title": "Book I, Ch. 2 — Having an Humble Conceit of Ourselves",
                "body_md": (
                    "Every man naturally desireth to know; but what doth knowledge avail without the fear of God?\n\n"
                    "Surely an humble husbandman that serveth God is better than a proud philosopher that, neglecting himself, considers the course of the heavens.\n\n"
                    "He that knoweth himself well, becometh mean in his own eyes, and is not delighted with the praises of men.\n\n"
                    "If I should know all things that are in the world, and should not be in charity, what would it help me before God, who will judge me by my deeds?\n\n"
                    "Rest from inordinate desire of knowledge, for therein is found much distraction and deceit. Such as are learned are desirous to seem so to others, and to be accounted wise.\n\n"
                    "There are many things, the knowledge of which is of little or no profit to the soul: and he is very unwise that is intent upon other things than those that may serve to his salvation."
                ),
            },
            {
                "title": "Book III, Ch. 5 — Of the Wonderful Effect of Divine Love",
                "body_md": (
                    "I bless Thee, O heavenly Father, Father of my Lord Jesus Christ, for that Thou hast vouchsafed to be mindful of me, poor as I am.\n\n"
                    "O Father of mercies, and God of all consolation, I give Thee thanks, who refresh me sometimes with Thy comfort, even when I am unworthy of any consolation.\n\n"
                    "I bless Thee always and glorify Thee with Thine only-begotten Son and the Holy Ghost the Paraclete, forever and ever.\n\n"
                    "Ah, Lord God, my holy Lover, when Thou shalt come into my heart, all that is within me will be filled with joy. Thou art my glory and the exultation of my heart. Thou art my hope and refuge in the day of my tribulation.\n\n"
                    "Love is a great thing, yea, a great and thorough good. By itself it makes everything that is heavy light; and it bears evenly all that is uneven. It carries a burden which is no burden; it makes every bitter thing sweet and tasteful.\n\n"
                    "Nothing is sweeter than love, nothing more courageous, nothing fuller, nor better in heaven and earth; for love is born of God, and cannot rest but in God, above all created things."
                ),
            },
        ],
    },

    # ---------- Story of a Soul ----------
    {
        "slug": "story-of-a-soul",
        "title": "Story of a Soul",
        "author": "St. Thérèse of Lisieux",
        "year": 1898,
        "blurb": "The 'Little Way' of total trust and tiny faithful acts of love, written under obedience by the Doctor of the Church who died at 24.",
        "tradition": "doctor",
        "cover_color": "#DB2777",
        "cover_icon": "rose",
        "type": "embedded",
        "source_url": "https://www.gutenberg.org/ebooks/16772",
        "chapters": [
            {
                "title": "Manuscript A — Springtime Story",
                "body_md": (
                    "It is to you, dear Mother, that I am going to confide the story of my soul. When you asked me to write it, I feared the task might unsettle me, but since then Jesus has made me feel that in obeying simply I should please Him.\n\n"
                    "I am only going to do one thing: to begin singing what I shall sing eternally — 'The Mercies of the Lord.'\n\n"
                    "Before taking up my pen I knelt before the statue of Mary (the one which has given so many proofs that the Queen of Heaven watches over our family), and I begged her to guide my hand so that I should not write one line displeasing to her.\n\n"
                    "I understand now that perfect charity consists in bearing with the faults of others, in not being surprised at their weakness, in being edified by the smallest acts of virtue we see them practice."
                ),
            },
            {
                "title": "The Little Way",
                "body_md": (
                    "I have always wanted to be a saint. Alas! I have always noticed that when I compared myself to the saints, there is between them and me the same difference that exists between a mountain whose summit is lost in the clouds and the obscure grain of sand trampled underfoot by passers-by.\n\n"
                    "Instead of becoming discouraged, I said to myself: God would not inspire me with desires which could not be realized; so in spite of my littleness, I can aim at being a saint. It is impossible for me to grow up, and so I must bear with myself such as I am with all my imperfections.\n\n"
                    "But I want to seek out a means of going to Heaven by a little way, a way that is very straight, very short, and totally new.\n\n"
                    "We are living now in an age of inventions, and we no longer have to take the trouble of climbing stairs, for, in the homes of the rich, an elevator has replaced these very successfully. I wanted to find an elevator which would raise me to Jesus, for I am too small to climb the rough stairway of perfection.\n\n"
                    "I searched, then, in the Scriptures for some sign of this elevator, the object of my desires, and I read these words coming from the mouth of Eternal Wisdom: 'Whoever is a LITTLE ONE, let him come to me' (Proverbs 9:4).\n\n"
                    "The elevator which must raise me to heaven is Your arms, O Jesus! And for this I had no need to grow up, but rather I had to remain little and become this more and more."
                ),
            },
        ],
    },

    # ---------- Confessions of St. Augustine ----------
    {
        "slug": "confessions-augustine",
        "title": "Confessions",
        "author": "St. Augustine of Hippo",
        "year": 400,
        "blurb": "The original spiritual autobiography. Augustine traces his restless heart from sin through Manichaeism to the embrace of Christ — and to a love that knows no end.",
        "tradition": "doctor",
        "cover_color": "#1E40AF",
        "cover_icon": "library-outline",
        "type": "embedded",
        "source_url": "https://www.ccel.org/ccel/augustine/confess.html",
        "chapters": [
            {
                "title": "Book I, Ch. 1 — Restless Hearts",
                "body_md": (
                    "Great art Thou, O Lord, and greatly to be praised; great is Thy power, and of Thy wisdom there is no end.\n\n"
                    "And man, being a part of Thy creation, desires to praise Thee — man, who bears about with him his mortality, the witness of his sin, even the witness that Thou 'resistest the proud,' — yet man, this part of Thy creation, desires to praise Thee.\n\n"
                    "Thou movest us to delight in praising Thee; for Thou hast formed us for Thyself, and our hearts are restless till they find rest in Thee.\n\n"
                    "Grant me, Lord, to know and understand which is first, — to call on Thee or to praise Thee? and likewise to know Thee or to call on Thee? But who calls upon Thee without knowing Thee?\n\n"
                    "For he that knoweth Thee not may call on Thee as other than Thou art. Or may it be that we call on Thee that we may know Thee?\n\n"
                    "But how shall they call on Him in whom they have not believed? And how shall they believe without a preacher? They shall praise the Lord that seek Him."
                ),
            },
            {
                "title": "Book VIII, Ch. 12 — Take Up and Read",
                "body_md": (
                    "I was weeping in the most bitter contrition of my heart, when, lo, I heard the voice as of a boy or girl, I know not which, coming from a neighboring house, chanting, and oft repeating, 'Take up and read; take up and read.'\n\n"
                    "Immediately my countenance was changed, and I began most earnestly to consider whether it was usual for children in any kind of game to sing such words; nor could I remember ever to have heard the like.\n\n"
                    "So, restraining the torrent of my tears, I rose up, interpreting it no other way than as a command to me from Heaven to open the book, and to read the first chapter I should light upon.\n\n"
                    "I grasped, opened, and in silence read that paragraph on which my eyes first fell: 'Not in rioting and drunkenness, not in chambering and wantonness, not in strife and envying; but put ye on the Lord Jesus Christ, and make not provision for the flesh, to fulfill the lusts thereof.'\n\n"
                    "No further would I read, nor did I need; for instantly, as the sentence ended, by a light, as it were, of security infused into my heart, all the gloom of doubt vanished away."
                ),
            },
            {
                "title": "Book X, Ch. 27 — Late Have I Loved Thee",
                "body_md": (
                    "Late have I loved Thee, O Beauty ever ancient, ever new, late have I loved Thee!\n\n"
                    "Behold, Thou wert within, and I abroad, and there I searched for Thee; deformed I, plunging amid those fair forms which Thou hadst made.\n\n"
                    "Thou wert with me, but I was not with Thee. Things held me far from Thee, which, unless they were in Thee, were not at all.\n\n"
                    "Thou calledst, and shoutedst, and burstest my deafness. Thou flashedst, shonest, and scatteredst my blindness. Thou breathedst odours, and I drew in breath and panted for Thee.\n\n"
                    "I tasted, and hunger and thirst. Thou touchedst me, and I burned for Thy peace.\n\n"
                    "When once I shall cleave to Thee with all my being, then shall I in no point have grief or labor; and my life shall wholly live, as wholly full of Thee."
                ),
            },
        ],
    },

    # ---------- Introduction to the Devout Life ----------
    {
        "slug": "devout-life",
        "title": "Introduction to the Devout Life",
        "author": "St. Francis de Sales",
        "year": 1609,
        "blurb": "A warm, eminently practical guide showing how anyone — married, single, working a normal job — can pursue holiness in the midst of ordinary life.",
        "tradition": "doctor",
        "cover_color": "#0EA5E9",
        "cover_icon": "leaf-outline",
        "type": "embedded",
        "source_url": "https://www.ccel.org/ccel/desales/devout_life.html",
        "chapters": [
            {
                "title": "Part I, Ch. 1 — A Description of True Devotion",
                "body_md": (
                    "Devotion, Philothea, is nothing else but a spiritual agility and vivacity by means of which charity works in us, or we by her, with promptitude and affection.\n\n"
                    "It belongs to charity to make us observe all God's commandments generally and without exception; but it belongs to devotion to make us observe them readily and diligently.\n\n"
                    "He that observes not the commandments cannot be esteemed either good or devout; but he must, in order to be good, observe the commandments; and in order to be devout, observe them not only well, but cheerfully, promptly, and with a good heart.\n\n"
                    "A man newly recovered from illness walks as much as is necessary, but slowly and heavily. So a sinner, being cured of his iniquity, walks as God commands, but slowly and heavily, until such time as he attains devotion; for then, like a man in perfect health, he not only walks, but runs and leaps forward in the way of God's commandments.\n\n"
                    "Devotion is no other thing than the ardor and prompt motion of charity. It is necessary for everyone to practice the devout life, each in his own state and calling."
                ),
            },
            {
                "title": "Part I, Ch. 3 — Devotion is Suitable to All Vocations",
                "body_md": (
                    "When God created the world, He commanded each tree to bring forth fruit after its kind; and even so He bids Christians, the living trees of His Church, to bring forth fruits of devotion, each one according to his kind and vocation.\n\n"
                    "A different exercise of devotion is required from a gentleman, an artisan, a servant, a prince, a widow, a wife, a maid. And not only this, but the practice of devotion must be accommodated to the strength, the employment, and the duties of each one in particular.\n\n"
                    "Tell me, Philothea, would it be fit that a bishop should desire to lead the solitary life of a Carthusian monk? And if married people should lay up nothing for the future, like the Capuchins? If the artisan should be all day at church like the religious? And the religious always exposed to public engagements for the service of his neighbor, like the bishop?\n\n"
                    "Would not such a devotion be ridiculous, irregular, and intolerable?\n\n"
                    "It is an error, nay, a heresy, to seek to banish the devout life from among soldiers, mechanics, princes, courts, married people. It is true, Philothea, that purely contemplative, monastic, and religious devotion cannot be exercised in these vocations; but, besides these three kinds of devotion, there are several others proper for perfecting those who live in secular conditions."
                ),
            },
        ],
    },

    # ---------- Abandonment to Divine Providence ----------
    {
        "slug": "abandonment-divine-providence",
        "title": "Abandonment to Divine Providence",
        "author": "Jean-Pierre de Caussade, SJ",
        "year": 1750,
        "blurb": "The 'sacrament of the present moment.' De Caussade teaches that the path to sanctity is hidden in fully accepting God's will in everything that happens, now.",
        "tradition": "mystic",
        "cover_color": "#059669",
        "cover_icon": "hourglass-outline",
        "type": "embedded",
        "source_url": "https://www.gutenberg.org/ebooks/52057",
        "chapters": [
            {
                "title": "Ch. 1 — Sanctity Made Easy",
                "body_md": (
                    "God still speaks today as He spoke to our fathers, when there were no spiritual directors nor any system of spirituality. Then sanctity was attained by fidelity to the order established by God.\n\n"
                    "God still speaks to us through the events and circumstances of our daily life. Sanctity does not consist in doing extraordinary things, but in accepting from God all that He sends in each present moment and uniting ourselves to His will.\n\n"
                    "The will of God is the substance of our sanctification; everything else is decoration. The duty of the present moment is the only thing God asks of us. Faithfulness to it in spite of difficulty makes saints.\n\n"
                    "The present moment is always full of infinite treasures; it contains more than you are capable of receiving. Faith measures it out to you. Faith makes you accept all that happens as a sample of God's love.\n\n"
                    "The whole essence of self-abandonment lies in this: in welcoming, with confident love, God's good pleasure, however it may manifest itself."
                ),
            },
            {
                "title": "Ch. 2 — The Sacrament of the Present Moment",
                "body_md": (
                    "The present moment is the ambassador of God who declares His mandates. The heart pronounces its fiat. The soul advances by means of these acts of submission.\n\n"
                    "What God arranges for us to experience at each moment is the best and holiest thing that could happen to us. We need only abandon ourselves to His order and direction, with a confidence as great as our nothingness, and with a self-surrender as complete as is His goodness.\n\n"
                    "God's order, His pleasure, His will, His work and divine action — all are one and the same thing in life. Souls in the state of pure faith have no other guide than the will of God, and the present moment.\n\n"
                    "Faith finds God in the most everyday and trivial events. There is no moment in which God does not present Himself under some cover — duty, attraction, inspiration — but always His will is manifest. The soul that lives by faith finds God in everything; nothing escapes its grasp."
                ),
            },
        ],
    },

    # ---------- Spiritual Combat ----------
    {
        "slug": "spiritual-combat",
        "title": "The Spiritual Combat",
        "author": "Lorenzo Scupoli",
        "year": 1589,
        "blurb": "A favorite of St. Francis de Sales — strategic instruction for the lifelong battle against self-love, the enemy, and our own disordered passions.",
        "tradition": "catholic-classic",
        "cover_color": "#7F1D1D",
        "cover_icon": "shield-outline",
        "type": "embedded",
        "source_url": "https://en.wikisource.org/wiki/The_Spiritual_Combat",
        "chapters": [
            {
                "title": "Ch. 1 — Wherein Christian Perfection Consists",
                "body_md": (
                    "If you would attain to the height of Christian perfection, my child, you must know that this excellence consists not in any of those exterior things that flesh and blood are wont to take notice of — to fast much, to wear hair-shirts, to give alms, to mortify the body — for though these be good and holy, they are nevertheless but the means and not the end.\n\n"
                    "Christian perfection consists in nothing else but in the knowledge of the divine goodness and greatness of God, and the knowledge of our own nothingness and inclinations to all evil; in the love of God, and the hatred of ourselves; in submission, not only to God Himself, but for the love of Him, to all His creatures; in the entire renunciation of our own will, and in a complete resignation of ourselves to all the divine pleasure.\n\n"
                    "If you would attain unto so great happiness, you must enter into a continual and furious battle against yourself, and you must employ the whole strength of your soul in pulling up and beating down, little by little, your evil inclinations, however slight and unimportant they may appear to be."
                ),
            },
        ],
    },

    # ---------- Interior Castle ----------
    {
        "slug": "interior-castle",
        "title": "The Interior Castle",
        "author": "St. Teresa of Ávila",
        "year": 1577,
        "blurb": "Teresa's masterwork — a tour of the seven mansions of the soul, leading inward toward union with God who dwells in the innermost chamber.",
        "tradition": "doctor",
        "cover_color": "#831843",
        "cover_icon": "diamond-outline",
        "type": "embedded",
        "source_url": "https://www.ewtn.com/catholicism/library/interior-castle-12568",
        "chapters": [
            {
                "title": "First Mansions, Ch. 1 — The Castle Within",
                "body_md": (
                    "While I was begging our Lord to-day that He would deign to speak through me, since I could find nothing to say and had no idea how to begin to obey this command laid upon me, a thought struck me which I will now explain.\n\n"
                    "We may liken our soul to a castle made of a single diamond or of very clear crystal, in which there are many rooms, just as in Heaven there are many mansions. For if we think it over carefully, sisters, the soul of the righteous is nothing but a paradise, in which, as God Himself tells us, He takes His delight.\n\n"
                    "What then must that dwelling be in which a King so mighty, so wise, so pure, so full of all good things can delight to live? I find nothing comparable to the great beauty of a soul and its immense capacity.\n\n"
                    "It is no slight pity and confusion that, through our own fault, we do not understand ourselves, nor know who we are. Would it not show great ignorance, my daughters, if anyone, when asked who he was, did not know, nor know his father nor his mother, nor from what country he came?\n\n"
                    "Though this is gross stupidity, our own is incomparably greater when we make no attempt to discover what we are, and only know that we are living in these bodies, and have a vague idea, because we have heard it and because our Faith tells us so, that we possess souls."
                ),
            },
            {
                "title": "Fourth Mansions, Ch. 3 — The Prayer of Quiet",
                "body_md": (
                    "Let us now begin to treat of the supernatural — what I call the Prayer of Quiet, in which the soul does not labor for what it possesses, but enjoys it without understanding how. There is no necessity to use force or to make any noise.\n\n"
                    "Note carefully, daughters, this comparison which our Lord put into my mind when I was in this state of prayer, which seems to me very apt. The waters in these basins are filled in different ways: the one comes from a great distance through many aqueducts and by human industry; the other has been made at the very source of the water and fills without any noise.\n\n"
                    "If the spring is plentiful, as is the case with us, after the basin has been filled, a great stream still flows from it; no skill is necessary, nor does the construction of aqueducts have to be kept up, but the water is continually flowing.\n\n"
                    "The difference between these two kinds of consolations in prayer is, in my opinion, this. The first comes through meditations and prayers, employing the imagination and helped by creatures. With the other, this is not so: God Himself produces it without any industry of our own, with the greatest peace and quietness and sweetness within us — I know not where, nor how."
                ),
            },
        ],
    },

    # ---------- True Devotion to Mary ----------
    {
        "slug": "true-devotion-mary",
        "title": "True Devotion to Mary",
        "author": "St. Louis-Marie de Montfort",
        "year": 1712,
        "blurb": "The classical treatise on Marian consecration, recovered in the 19th century and beloved by St. John Paul II — 'Totus Tuus.'",
        "tradition": "mystic",
        "cover_color": "#1E3A8A",
        "cover_icon": "star-outline",
        "type": "embedded",
        "source_url": "https://www.ewtn.com/catholicism/library/treatise-on-true-devotion-to-the-blessed-virgin-6064",
        "chapters": [
            {
                "title": "Introduction — Why Through Mary?",
                "body_md": (
                    "It was through the Blessed Virgin Mary that Jesus came into the world, and it is also through her that He must reign in the world.\n\n"
                    "Mary was very little known during the early ages of the Church. The Holy Ghost did not see fit to manifest her further in those days, because the divinity of her Son was not as yet sufficiently established; and if Mary had been too well known, it might have led to a danger of His not being adored as God.\n\n"
                    "But in these latter times, Mary must shine forth more than ever in mercy, in might, and in grace; in mercy, to bring back and lovingly receive the poor sinners who shall be converted and shall return to the Catholic Church; in might, to combat the enemies of God; and in grace, to animate and sustain the valiant soldiers and faithful servants of Jesus Christ.\n\n"
                    "Finally, Mary must be terrible to the devil and his followers, as an army ranged in battle, principally in these latter times; because the devil, knowing that he has but little time to ruin souls, redoubles his efforts and his combats every day."
                ),
            },
        ],
    },

    # ---------- Treatise on Purgatory ----------
    {
        "slug": "treatise-purgatory",
        "title": "Treatise on Purgatory",
        "author": "St. Catherine of Genoa",
        "year": 1510,
        "blurb": "Short, luminous reflections born of intense mystical experience — purgatory not as a place of dread but of God's purifying love.",
        "tradition": "mystic",
        "cover_color": "#EA580C",
        "cover_icon": "flame",
        "type": "embedded",
        "source_url": "https://www.ewtn.com/catholicism/library/treatise-on-purgatory-9820",
        "chapters": [
            {
                "title": "Ch. 2 — The State of Souls in Purgatory",
                "body_md": (
                    "The souls in purgatory cannot, as I understand, choose but be there, and this is by God's just decree; neither can they turn their attention to themselves, nor can they say: 'Such sins I have committed for which I deserve to be here,' nor: 'I would I had not committed them so that I might now go to paradise,' nor: 'That one will leave sooner than I,' nor: 'I will leave sooner than he.'\n\n"
                    "They can have neither of themselves nor of others any memory, either of good or of evil, whereby they should be more pained than they are. So happy are they to be within God's appointment, and that He should do all which pleases Him, as it pleases Him, that they cannot think of themselves though they try ever so hard.\n\n"
                    "They see nothing but the working of the divine goodness, which mercy is so manifestly bringing them to God. They are unable to think: 'I am here, and justly, for such and such sins.' They live in charity from which they cannot deviate by any thought of offense or hindrance toward God.\n\n"
                    "I see also rays of love going forth from that loving heart of God, which dart into these souls in purgatory with such grace and tenderness, that they go forth confiding in His mercy."
                ),
            },
        ],
    },

    # ---------- EXTERNAL: Catechism of the Catholic Church ----------
    {
        "slug": "catechism-catholic-church",
        "title": "Catechism of the Catholic Church",
        "author": "Roman Catholic Church",
        "year": 1992,
        "blurb": "The complete, official Catechism in English, hosted by the Vatican. The summary statement of all Catholic faith and practice.",
        "tradition": "catholic-classic",
        "cover_color": "#374151",
        "cover_icon": "library",
        "type": "external",
        "source_url": "https://www.vatican.va/archive/ENG0015/_INDEX.HTM",
        "chapters": [],
    },

    # ---------- EXTERNAL: Summa Theologica ----------
    {
        "slug": "summa-theologica",
        "title": "Summa Theologica",
        "author": "St. Thomas Aquinas",
        "year": 1274,
        "blurb": "The masterwork of Catholic theology and philosophy — the Angelic Doctor's systematic treatment of God, creation, virtue, and the sacraments.",
        "tradition": "doctor",
        "cover_color": "#92400E",
        "cover_icon": "telescope-outline",
        "type": "external",
        "source_url": "https://www.newadvent.org/summa/",
        "chapters": [],
    },

    # ---------- EMBEDDED: Orthodoxy (full text via Gutenberg #130) ----------
    {
        "slug": "orthodoxy-chesterton",
        "title": "Orthodoxy",
        "author": "G.K. Chesterton",
        "year": 1908,
        "blurb": "Chesterton's joyful, paradoxical defense of the Christian creed — the story of how he came to believe what he calls 'the most reasonable thing in the world.'",
        "tradition": "apologist",
        "cover_color": "#581C87",
        "cover_icon": "umbrella-outline",
        "type": "embedded",
        "source_url": "https://www.gutenberg.org/ebooks/130",
        "chapters": [],
    },

    # ---------- EXTERNAL: Apologia Pro Vita Sua ----------
    {
        "slug": "apologia-pro-vita-sua",
        "title": "Apologia Pro Vita Sua",
        "author": "St. John Henry Newman",
        "year": 1864,
        "blurb": "St. John Henry Newman's stirring account of his conversion from Anglicanism to Catholicism — a luminous chapter in 19th-century English letters.",
        "tradition": "apologist",
        "cover_color": "#0F172A",
        "cover_icon": "compass-outline",
        "type": "external",
        "source_url": "https://www.newmanreader.org/works/apologia65/index.html",
        "chapters": [],
    },

    # ---------- EXTERNAL: The Everlasting Man ----------
    {
        "slug": "everlasting-man",
        "title": "The Everlasting Man",
        "author": "G.K. Chesterton",
        "year": 1925,
        "blurb": "Chesterton answers H.G. Wells with a sweeping Catholic vision of the history of humanity from cave-art to the Incarnation.",
        "tradition": "apologist",
        "cover_color": "#9A3412",
        "cover_icon": "earth-outline",
        "type": "external",
        "source_url": "https://gutenberg.net.au/ebooks01/0100311h.html",
        "chapters": [],
    },
]



# ---------------------------------------------------------------------------
# Phase 2 — Radio stations
# ---------------------------------------------------------------------------
# Each entry:
#   slug, name, blurb, country, language, stream_url, website_url,
#   accent_color, icon
#
# Stream URLs are public HLS/MP3 endpoints published by each station.
# Update via /api/library/admin/radio if a station rotates a URL.

SEED_STATIONS: List[Dict[str, Any]] = [
    {
        "slug": "ewtn-radio",
        "name": "EWTN Catholic Radio",
        "blurb": "The flagship 24/7 English-language Catholic network — Mass, rosary, talk shows, and catechesis from Mother Angelica's broadcast family.",
        "country": "US",
        "language": "English",
        "stream_url": "https://ewtn-ice.streamguys1.com/english-aac",
        "website_url": "https://www.ewtn.com/radio",
        "accent_color": "#1E40AF",
        "icon": "radio-outline",
    },
    {
        "slug": "relevant-radio",
        "name": "Relevant Radio",
        "blurb": "Talk radio with a Catholic worldview — daily rosary, Drew Mariani, Father Rocky, and 24-hour spiritual companionship.",
        "country": "US",
        "language": "English",
        "stream_url": "https://playerservices.streamtheworld.com/api/livestream-redirect/RR_MAIN.mp3",
        "website_url": "https://relevantradio.com/listen/",
        "accent_color": "#7C3AED",
        "icon": "mic-outline",
    },
    {
        "slug": "iowa-catholic-radio",
        "name": "Iowa Catholic Radio",
        "blurb": "A regional Catholic powerhouse — sacred music, daily Mass, and Iowa's voice for the faith.",
        "country": "US",
        "language": "English",
        "stream_url": "https://streaming.live365.com/a39922?n=15e4d1f6f58efdde0d65",
        "website_url": "https://iowacatholicradio.com/",
        "accent_color": "#B45309",
        "icon": "musical-notes-outline",
    },
    {
        "slug": "real-presence-radio",
        "name": "Real Presence Radio",
        "blurb": "From Fargo, ND — daily Mass, the holy rosary, and prayerful programming centered on the Eucharist.",
        "country": "US",
        "language": "English",
        "stream_url": "https://ssl-1.stream.miriamtech.net/realpresence/kwtl",
        "website_url": "https://realpresenceradio.com/",
        "accent_color": "#9E1B1B",
        "icon": "heart-outline",
    },
    {
        "slug": "guadalupe-radio",
        "name": "Guadalupe Radio Network",
        "blurb": "Texas-rooted bilingual Catholic network with strong devotion to Our Lady of Guadalupe.",
        "country": "US",
        "language": "English",
        "stream_url": "https://ssl-2.stream.miriamtech.net/grn/secal.mp3",
        "website_url": "https://grnonline.com/",
        "accent_color": "#059669",
        "icon": "star-outline",
    },
    {
        "slug": "irosary-radio",
        "name": "iRosary Radio",
        "blurb": "Continuous holy rosary, divine mercy chaplet, and Catholic devotionals — perfect background prayer companion.",
        "country": "US",
        "language": "English",
        "stream_url": "https://stream.radio.co/sbc212800b/low",
        "website_url": "https://www.irosaryradio.com/",
        "accent_color": "#0EA5E9",
        "icon": "rose-outline",
    },
    {
        "slug": "vatican-news-english",
        "name": "Vatican News — English",
        "blurb": "Official voice of the Holy See in English — Pope's homilies, Angelus, and Catholic news from Rome.",
        "country": "Vatican",
        "language": "English",
        "stream_url": "https://radio.vaticannews.va/stream-en",
        "website_url": "https://www.vaticannews.va/en/podcast.html",
        "accent_color": "#374151",
        "icon": "earth-outline",
    },
    {
        "slug": "ewtn-espanol",
        "name": "EWTN Radio Católica Mundial",
        "blurb": "The Spanish-language voice of EWTN — Misa, rosario, and Catholic teaching for the Hispanic world.",
        "country": "US",
        "language": "Spanish",
        "stream_url": "https://ewtn-ice.streamguys1.com/spanish-aac",
        "website_url": "https://www.ewtn.com/spanish",
        "accent_color": "#831843",
        "icon": "flower-outline",
    },
]


# ---------------------------------------------------------------------------
# Phase 3 — Catholic films (YouTube only)
# ---------------------------------------------------------------------------
# Each entry:
#   slug, title, blurb, youtube_id, duration_label, category, accent_color
# category ∈ saints | doctrine | animated | documentary

SEED_FILMS: List[Dict[str, Any]] = [
    # ---- Saints ----
    {
        "slug": "molokai-damien",
        "title": "Molokai: The Story of Father Damien",
        "blurb": "The award-winning 1999 film starring David Wenham as St. Damien of Molokai — his heroic ministry to lepers in the Hawaiian Islands.",
        "youtube_id": "AweoZYsiCu4",
        "duration_label": "1h 58m",
        "category": "saints",
        "accent_color": "#0EA5E9",
    },
    {
        "slug": "padre-pio-miracle",
        "title": "Padre Pio (2000) — Sergio Castellitto",
        "blurb": "The full feature-length Italian film of the stigmatic Capuchin friar, canonized by John Paul II. (Italian audio)",
        "youtube_id": "5C27CJyspZc",
        "duration_label": "3h 22m",
        "category": "saints",
        "accent_color": "#7C3AED",
    },
    {
        "slug": "bernadette-1943",
        "title": "The Song of Bernadette (1943)",
        "blurb": "The Academy Award-winning classic of St. Bernadette Soubirous and the apparitions at Lourdes — full feature with Jennifer Jones.",
        "youtube_id": "muoFcCkR8NQ",
        "duration_label": "2h 36m",
        "category": "saints",
        "accent_color": "#1E40AF",
    },
    # ---- Doctrine ----
    {
        "slug": "barron-mass",
        "title": "Bishop Barron on the Mass",
        "blurb": "A lucid teaching from Bishop Robert Barron walking through the call-and-response structure and meaning of the Catholic Mass.",
        "youtube_id": "pIGXtDR2GCk",
        "duration_label": "15m",
        "category": "doctrine",
        "accent_color": "#B45309",
    },
    {
        "slug": "barron-eucharist",
        "title": "The Real Presence of Jesus in the Eucharist",
        "blurb": "Bishop Barron's full 2020 Religious Education Congress keynote on the Eucharist as the source and summit of Catholic life.",
        "youtube_id": "UzCPu_lEhe8",
        "duration_label": "1h 12m",
        "category": "doctrine",
        "accent_color": "#9A3412",
    },
    {
        "slug": "scott-hahn-conversion",
        "title": "Scott Hahn — A Presbyterian Minister Who Became Catholic",
        "blurb": "The Journey Home (EWTN) feature: Scott Hahn's now-famous conversion story and how the Scriptures led him home to Rome.",
        "youtube_id": "XilzGLfgd7A",
        "duration_label": "56m",
        "category": "doctrine",
        "accent_color": "#7F1D1D",
    },
    # ---- Animated / For Kids ----
    {
        "slug": "st-francis-animated",
        "title": "Saint Francis of Assisi — Full Animated Movie",
        "blurb": "A feature-length animated retelling of the Poverello of Assisi for the whole family.",
        "youtube_id": "lutB_jV7IyE",
        "duration_label": "1h 22m",
        "category": "animated",
        "accent_color": "#EA580C",
    },
    {
        "slug": "ccc-bernadette-anim",
        "title": "Lady of Guadeloupe",
        "blurb": "Skeptical of modern-day Christianity, a young reporter investigates the legend of Juan Diego and Our Lady of Guadalupe.",
        "youtube_id": "ACBWU4ug-rc",
        "duration_label": "Feature",
        "category": "saints",
        "accent_color": "#0EA5E9",
    },
    {
        "slug": "juan-diego-anim",
        "title": "Our Lady of Guadalupe & Saint Juan Diego (Animated for Kids)",
        "blurb": "The miracle of Tepeyac brought to life for children — the apparition, the roses, and the tilma.",
        "youtube_id": "FI_gXWGmBNg",
        "duration_label": "28m",
        "category": "animated",
        "accent_color": "#059669",
    },
    # ---- Documentary ----
    {
        "slug": "guadalupe-doc",
        "title": "Guadalupe — The Miracle and the Message",
        "blurb": "A full documentary on the apparitions of Our Lady of Guadalupe and the scientific examination of the tilma.",
        "youtube_id": "ym-b05cTZdM",
        "duration_label": "58m",
        "category": "documentary",
        "accent_color": "#374151",
    },
    {
        "slug": "shroud-of-turin-doc",
        "title": "Mystery of the Sacred Shroud (1997)",
        "blurb": "Narrated by Richard Burton — an examination of the most studied artifact in human history and what it tells us about the Passion.",
        "youtube_id": "io8WUa-wTIk",
        "duration_label": "1h 25m",
        "category": "documentary",
        "accent_color": "#831843",
    },
    {
        "slug": "john-paul-ii-papacy",
        "title": "How a Polish Boy Became the Pope — John Paul II",
        "blurb": "A full mini-series biography on the life of St. John Paul II, from his Polish childhood to the chair of Peter.",
        "youtube_id": "2gpvfvhcRGc",
        "duration_label": "1h 30m",
        "category": "documentary",
        "accent_color": "#1E40AF",
    },
]
