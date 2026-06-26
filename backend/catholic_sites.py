"""Catholic World Map — churches, basilicas, shrines & apparition sites.

A curated atlas of significant Catholic places around the world. Each site
carries its coordinates, a short blurb, a longer history, and — where they
exist — the relics it holds, the saints connected to it, and notable
miracles/apparitions associated with the place.

The data is hand-curated for accuracy (Catholic content should not be
hallucinated). String fields are localized on demand via the shared
translation cache, exactly like the miracles feed.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from lang_ctx import get_lang

# Site categories used for marker colours / filtering on the client.
TYPES = {"basilica", "cathedral", "shrine", "apparition", "monastery", "church"}

# --------------------------------------------------------------------------- #
# Curated seed — famous, accurately-described Catholic sites.                  #
# --------------------------------------------------------------------------- #
SEED_SITES: List[Dict[str, Any]] = [
    {
        "slug": "st-peters-basilica",
        "name": "St. Peter's Basilica",
        "type": "basilica", "city": "Vatican City", "country": "Vatican City",
        "lat": 41.9022, "lng": 12.4539, "founded": "1506–1626",
        "blurb": "The heart of the Catholic Church, built over the tomb of St. Peter the Apostle.",
        "history": "Constantine raised the first basilica here in the 4th century over the burial site of "
        "St. Peter. The present Renaissance basilica — designed by Bramante, Michelangelo, Maderno and "
        "Bernini — is the largest church in the world and the principal site of papal liturgies.",
        "relics": ["Tomb and bones of St. Peter the Apostle (beneath the high altar)", "Relics of St. John Chrysostom", "The Veronica veil (claimed)"],
        "saints": ["St. Peter the Apostle", "Pope St. John Paul II (entombed here)", "Pope St. John XXIII"],
        "miracles": ["Numerous canonization miracles confirmed for saints entombed or venerated here"],
        "source_url": "https://www.vaticanstate.va/en/monuments/st-peters-basilica.html",
    },
    {
        "slug": "our-lady-of-guadalupe",
        "name": "Basilica of Our Lady of Guadalupe",
        "type": "apparition", "city": "Mexico City", "country": "Mexico",
        "lat": 19.4846, "lng": -99.1177, "founded": "1531 (apparition); 1976 (new basilica)",
        "blurb": "Home of the miraculous tilma of St. Juan Diego, the most visited Marian shrine on earth.",
        "history": "In December 1531 the Virgin Mary appeared to St. Juan Diego at Tepeyac, leaving her "
        "image imprinted on his tilma (cloak). The cactus-fibre cloth, which should have decayed within "
        "decades, survives nearly 500 years later and is venerated by millions each year.",
        "relics": ["The tilma (cloak) of St. Juan Diego bearing the image of Our Lady of Guadalupe"],
        "saints": ["St. Juan Diego Cuauhtlatoatzin"],
        "miracles": ["The imprinted image of Our Lady of Guadalupe", "Preservation of the tilma", "Eyes of the image reportedly reflect figures present in 1531"],
        "source_url": "https://www.britannica.com/topic/Our-Lady-of-Guadalupe",
    },
    {
        "slug": "lourdes",
        "name": "Sanctuary of Our Lady of Lourdes",
        "type": "apparition", "city": "Lourdes", "country": "France",
        "lat": 43.0978, "lng": -0.0558, "founded": "1858 (apparitions)",
        "blurb": "Site of the apparitions to St. Bernadette and a spring associated with thousands of healings.",
        "history": "In 1858 the Virgin Mary appeared eighteen times to St. Bernadette Soubirous in the grotto "
        "of Massabielle, identifying herself as 'the Immaculate Conception.' A spring uncovered by Bernadette "
        "is linked to many cures; 70 have been officially recognised by the Church as miraculous.",
        "relics": ["Relics of St. Bernadette Soubirous"],
        "saints": ["St. Bernadette Soubirous"],
        "miracles": ["70 Church-recognised miraculous healings", "The miraculous spring of Lourdes"],
        "source_url": "https://www.lourdes-france.org/en/",
    },
    {
        "slug": "fatima",
        "name": "Sanctuary of Our Lady of Fátima",
        "type": "apparition", "city": "Fátima", "country": "Portugal",
        "lat": 39.6317, "lng": -8.6722, "founded": "1917 (apparitions)",
        "blurb": "Where Our Lady appeared to three shepherd children and the 'Miracle of the Sun' occurred.",
        "history": "In 1917 the Virgin Mary appeared six times to Lúcia, Francisco and Jacinta. On 13 October "
        "a crowd of tens of thousands reported the sun 'dancing' in the sky. The apparitions, with their call "
        "to prayer and penance, were declared worthy of belief in 1930.",
        "relics": ["Tombs of Sts. Francisco and Jacinta Marto"],
        "saints": ["St. Francisco Marto", "St. Jacinta Marto", "Servant of God Sr. Lúcia"],
        "miracles": ["The Miracle of the Sun (13 Oct 1917)"],
        "source_url": "https://www.fatima.pt/en",
    },
    {
        "slug": "santiago-de-compostela",
        "name": "Cathedral of Santiago de Compostela",
        "type": "cathedral", "city": "Santiago de Compostela", "country": "Spain",
        "lat": 42.8806, "lng": -8.5446, "founded": "1075–1211",
        "blurb": "Goal of the Camino de Santiago pilgrimage, holding the relics of St. James the Greater.",
        "history": "Built over the reputed tomb of the Apostle James the Greater, discovered in the 9th "
        "century, the cathedral became the destination of medieval Europe's greatest pilgrimage, the Camino "
        "de Santiago, still walked by hundreds of thousands each year.",
        "relics": ["Relics of St. James the Greater, Apostle"],
        "saints": ["St. James the Greater, Apostle"],
        "miracles": ["Discovery of the apostle's tomb guided by a field of stars ('campus stellae')"],
        "source_url": "https://catedraldesantiago.es/en/",
    },
    {
        "slug": "lanciano",
        "name": "Church of San Francesco (Lanciano)",
        "type": "church", "city": "Lanciano", "country": "Italy",
        "lat": 42.2306, "lng": 14.3903, "founded": "8th century miracle",
        "blurb": "Home of the Eucharistic Miracle of Lanciano — host and wine became flesh and blood.",
        "history": "Around 750 AD, during Mass, a doubting priest saw the host turn to flesh and the wine to "
        "blood. The relics are still preserved; 20th-century scientific studies identified human cardiac "
        "tissue and type-AB blood.",
        "relics": ["The flesh and blood of the Eucharistic Miracle of Lanciano"],
        "saints": [],
        "miracles": ["The Eucharistic Miracle of Lanciano (c. 750 AD)"],
        "source_url": "https://www.ewtn.com/catholicism/library/eucharistic-miracle-of-lanciano-4983",
    },
    {
        "slug": "assisi-basilica",
        "name": "Basilica of St. Francis of Assisi",
        "type": "basilica", "city": "Assisi", "country": "Italy",
        "lat": 43.0747, "lng": 12.6056, "founded": "1228–1253",
        "blurb": "Burial place of St. Francis, and near the resting place of Bl. Carlo Acutis.",
        "history": "Begun two years after the death of St. Francis in 1226, the basilica's upper and lower "
        "churches are adorned with frescoes by Giotto and Cimabue. Assisi remains a centre of Franciscan "
        "spirituality and pilgrimage.",
        "relics": ["Tomb of St. Francis of Assisi", "The habit and relics of St. Francis"],
        "saints": ["St. Francis of Assisi", "Bl. Carlo Acutis (nearby, Santa Maria Maggiore)"],
        "miracles": ["St. Francis's stigmata (received at La Verna, 1224)"],
        "source_url": "https://www.sanfrancescoassisi.org/en/",
    },
    {
        "slug": "san-giovanni-rotondo",
        "name": "Shrine of St. Pio of Pietrelcina",
        "type": "shrine", "city": "San Giovanni Rotondo", "country": "Italy",
        "lat": 41.7064, "lng": 15.7297, "founded": "1959 / 2004",
        "blurb": "Resting place of St. Padre Pio, the stigmatic friar of the 20th century.",
        "history": "St. Pio bore the visible wounds of Christ for fifty years and was renowned for "
        "bilocation, healings, and reading souls in confession. His incorrupt body is venerated here; the "
        "modern shrine designed by Renzo Piano draws millions of pilgrims.",
        "relics": ["Incorrupt body of St. Pio of Pietrelcina"],
        "saints": ["St. Pio of Pietrelcina (Padre Pio)"],
        "miracles": ["The stigmata of Padre Pio", "Documented healings through his intercession"],
        "source_url": "https://www.conventosantamariadellegrazie.it/en/",
    },
    {
        "slug": "notre-dame-de-paris",
        "name": "Notre-Dame de Paris",
        "type": "cathedral", "city": "Paris", "country": "France",
        "lat": 48.8530, "lng": 2.3499, "founded": "1163–1345",
        "blurb": "The great Gothic cathedral of Paris, keeper of the Crown of Thorns.",
        "history": "A masterpiece of French Gothic architecture begun in 1163, Notre-Dame survived revolution "
        "and the 2019 fire and was restored and reopened in 2024. It safeguards relics of the Passion.",
        "relics": ["The Crown of Thorns", "A nail and a fragment of the True Cross"],
        "saints": ["St. Louis IX of France (who brought the Crown of Thorns to Paris)"],
        "miracles": ["The Crown of Thorns survived the 2019 fire unharmed"],
        "source_url": "https://www.notredamedeparis.fr/en/",
    },
    {
        "slug": "st-marys-major",
        "name": "Basilica of Santa Maria Maggiore",
        "type": "basilica", "city": "Rome", "country": "Italy",
        "lat": 41.8975, "lng": 12.4983, "founded": "432–440",
        "blurb": "The greatest Marian church in Rome, holding relics of the Holy Crib.",
        "history": "Built after the Council of Ephesus (431) proclaimed Mary 'Mother of God,' the basilica "
        "is said to have been marked out by a miraculous summer snowfall. It guards relics of the manger of "
        "Bethlehem and is the burial place of Pope Francis.",
        "relics": ["Relics of the Holy Crib (manger) of Bethlehem", "Relics of St. Jerome (reputed)"],
        "saints": ["St. Jerome", "Pope Francis (entombed here, 2025)"],
        "miracles": ["The miraculous summer snowfall of 5 August (Our Lady of the Snows)"],
        "source_url": "https://www.vatican.va/various/basiliche/sm_maggiore/index_en.html",
    },
    {
        "slug": "knock-shrine",
        "name": "Knock Shrine",
        "type": "apparition", "city": "Knock", "country": "Ireland",
        "lat": 53.7906, "lng": -8.9189, "founded": "1879 (apparition)",
        "blurb": "Site of the silent 1879 apparition of Our Lady, St. Joseph and St. John.",
        "history": "On 21 August 1879, fifteen villagers witnessed an apparition of the Blessed Virgin, St. "
        "Joseph, St. John the Evangelist and a Lamb on an altar at the gable of the parish church. The "
        "apparition was silent and was investigated and approved; Knock is now a national Marian shrine.",
        "relics": [],
        "saints": ["St. Joseph", "St. John the Evangelist (depicted in the apparition)"],
        "miracles": ["The Knock apparition (1879)", "Reported healings at the shrine"],
        "source_url": "https://www.knockshrine.ie/",
    },
    {
        "slug": "czestochowa",
        "name": "Jasna Góra Monastery (Black Madonna)",
        "type": "monastery", "city": "Częstochowa", "country": "Poland",
        "lat": 50.8121, "lng": 19.0968, "founded": "1382",
        "blurb": "Spiritual capital of Poland, home of the miraculous icon of the Black Madonna.",
        "history": "The Pauline monastery of Jasna Góra enshrines the venerated icon of Our Lady of "
        "Częstochowa, attributed by tradition to St. Luke. Credited with defending the monastery during the "
        "1655 Swedish siege, the icon is a powerful symbol of Polish faith and identity.",
        "relics": ["The icon of Our Lady of Częstochowa (the Black Madonna)"],
        "saints": ["Connected with St. John Paul II's devotion"],
        "miracles": ["Defense of Jasna Góra during the 1655 siege", "Healings attributed to the icon"],
        "source_url": "https://www.jasnagora.com/",
    },
    {
        "slug": "basilica-national-shrine-dc",
        "name": "Basilica of the National Shrine of the Immaculate Conception",
        "type": "basilica", "city": "Washington, D.C.", "country": "United States",
        "lat": 38.9333, "lng": -76.9986, "founded": "1920–1959",
        "blurb": "The largest Catholic church in North America, dedicated to the Immaculate Conception.",
        "history": "Patronal church of the United States, the basilica honours Mary under her title of the "
        "Immaculate Conception. It holds more than 80 chapels reflecting devotions of peoples from around "
        "the world.",
        "relics": ["Relics of St. John Paul II and many saints in its chapels"],
        "saints": ["St. John Neumann", "St. Elizabeth Ann Seton (American saints honoured here)"],
        "miracles": [],
        "source_url": "https://www.nationalshrine.org/",
    },
    {
        "slug": "sagrada-familia",
        "name": "Basílica de la Sagrada Família",
        "type": "basilica", "city": "Barcelona", "country": "Spain",
        "lat": 41.4036, "lng": 2.1744, "founded": "1882–present",
        "blurb": "Gaudí's still-unfinished masterpiece, consecrated by Pope Benedict XVI in 2010.",
        "history": "Antoni Gaudí devoted the last decades of his life to this extraordinary basilica, a "
        "sermon in stone on the life of Christ. Gaudí, whose cause for canonization is open, is buried in "
        "its crypt; the church was consecrated in 2010.",
        "relics": [],
        "saints": ["Servant of God Antoni Gaudí (buried in the crypt)"],
        "miracles": [],
        "source_url": "https://sagradafamilia.org/en/home",
    },
    {
        "slug": "holy-sepulchre",
        "name": "Church of the Holy Sepulchre",
        "type": "church", "city": "Jerusalem", "country": "Israel/Palestine",
        "lat": 31.7784, "lng": 35.2297, "founded": "326–335",
        "blurb": "Built over Calvary and the empty tomb — the holiest site in Christianity.",
        "history": "Constructed by order of Constantine over the sites of Christ's crucifixion, burial and "
        "resurrection, the church is shared by several Christian communions. The aedicule encloses the tomb "
        "of Christ.",
        "relics": ["The Stone of Anointing", "Calvary (Golgotha)", "The empty Tomb of Christ"],
        "saints": ["St. Helena (who located the holy sites)"],
        "miracles": ["The Holy Fire, reported each Holy Saturday"],
        "source_url": "https://www.britannica.com/topic/Church-of-the-Holy-Sepulchre",
    },
    {
        "slug": "basilica-st-john-lateran",
        "name": "Archbasilica of St. John Lateran",
        "type": "basilica", "city": "Rome", "country": "Italy",
        "lat": 41.8858, "lng": 12.5057, "founded": "324",
        "blurb": "The cathedral of Rome and 'mother of all churches' in the world.",
        "history": "The oldest public church in Rome and the official seat (cathedra) of the Pope as Bishop "
        "of Rome. Nearby, the Scala Sancta is venerated as the steps Christ climbed before Pilate.",
        "relics": ["Relics of the heads of Sts. Peter and Paul (reputed)", "The Holy Stairs (Scala Sancta) nearby"],
        "saints": ["Sts. Peter and Paul (relics venerated)"],
        "miracles": [],
        "source_url": "https://www.vatican.va/various/basiliche/san_giovanni/index_en.html",
    },
    {
        "slug": "padua-st-anthony",
        "name": "Basilica of St. Anthony of Padua",
        "type": "basilica", "city": "Padua", "country": "Italy",
        "lat": 45.4014, "lng": 11.8810, "founded": "1232–1310",
        "blurb": "Resting place of St. Anthony, with his famously incorrupt tongue.",
        "history": "Built shortly after St. Anthony's death in 1231, 'Il Santo' is among the most visited "
        "shrines in the world. When his tomb was opened, his tongue was found incorrupt — a sign of his "
        "great gift of preaching.",
        "relics": ["Incorrupt tongue and jaw of St. Anthony", "Tomb of St. Anthony"],
        "saints": ["St. Anthony of Padua"],
        "miracles": ["The incorrupt tongue of St. Anthony", "Many miracles of intercession"],
        "source_url": "https://www.santantonio.org/en",
    },
    {
        "slug": "guadalupe-extremadura",
        "name": "Royal Monastery of Santa María de Guadalupe",
        "type": "monastery", "city": "Guadalupe (Cáceres)", "country": "Spain",
        "lat": 39.4520, "lng": -5.3289, "founded": "14th century",
        "blurb": "A UNESCO shrine of the Spanish Virgin of Guadalupe, tied to the discovery of the Americas.",
        "history": "This Hieronymite monastery houses a venerated dark statue of the Virgin. It was at "
        "Guadalupe that Columbus's voyages were tied; the first Native Americans were baptized in its font.",
        "relics": ["The statue of Our Lady of Guadalupe of Extremadura"],
        "saints": [],
        "miracles": ["Miracles long associated with the Marian image"],
        "source_url": "https://whc.unesco.org/en/list/665/",
    },
    {
        "slug": "monte-cassino",
        "name": "Abbey of Monte Cassino",
        "type": "monastery", "city": "Cassino", "country": "Italy",
        "lat": 41.4892, "lng": 13.8136, "founded": "529",
        "blurb": "Cradle of Western monasticism, founded by St. Benedict.",
        "history": "Founded by St. Benedict around 529, where he wrote his Rule that shaped Western monastic "
        "life. Destroyed several times — most recently in 1944 — and faithfully rebuilt each time.",
        "relics": ["Tomb of St. Benedict and St. Scholastica"],
        "saints": ["St. Benedict of Nursia", "St. Scholastica"],
        "miracles": ["Miracles recorded in St. Gregory the Great's life of St. Benedict"],
        "source_url": "https://www.abbaziamontecassino.org/",
    },
    {
        "slug": "ars-france",
        "name": "Shrine of St. John Vianney (Ars)",
        "type": "shrine", "city": "Ars-sur-Formans", "country": "France",
        "lat": 45.9981, "lng": 4.8233, "founded": "19th century",
        "blurb": "Parish of the Curé of Ars, patron of priests, whose incorrupt body rests here.",
        "history": "St. John Vianney transformed the village of Ars through tireless confession and "
        "holiness, drawing pilgrims from across France. His incorrupt body is venerated in the basilica.",
        "relics": ["Incorrupt body of St. John Vianney", "His heart (venerated separately)"],
        "saints": ["St. John Vianney (the Curé of Ars)"],
        "miracles": ["Healings and conversions attributed to the Curé"],
        "source_url": "https://www.arsnet.org/en/",
    },
    {
        "slug": "loreto-holy-house",
        "name": "Basilica of the Holy House of Loreto",
        "type": "shrine", "city": "Loreto", "country": "Italy",
        "lat": 43.4406, "lng": 13.6097, "founded": "13th century",
        "blurb": "Enshrines the Holy House of Nazareth, by tradition the home of the Holy Family.",
        "history": "According to tradition, the house of the Annunciation in Nazareth was translated to "
        "Loreto in the late 13th century. It is one of the most important Marian shrines in Italy and the "
        "patronal shrine of aviators.",
        "relics": ["The Holy House of Nazareth"],
        "saints": ["The Holy Family (venerated here)"],
        "miracles": ["The translation of the Holy House"],
        "source_url": "https://www.santuarioloreto.it/",
    },
    {
        "slug": "guadalupe-manila",
        "name": "Minor Basilica of the Black Nazarene (Quiapo Church)",
        "type": "basilica", "city": "Manila", "country": "Philippines",
        "lat": 14.5986, "lng": 120.9842, "founded": "1933 (present church)",
        "blurb": "Home of the Black Nazarene, focus of one of the world's largest devotions.",
        "history": "The dark statue of Jesus carrying the Cross, brought from Mexico in 1606, survived fires "
        "and earthquakes. Its annual Traslación procession draws millions of devotees.",
        "relics": ["The image of the Black Nazarene"],
        "saints": [],
        "miracles": ["Healings reported through the Black Nazarene", "Survival of the image through fires and earthquakes"],
        "source_url": "https://quiapochurch.com/",
    },
    {
        "slug": "basilica-our-lady-aparecida",
        "name": "Basilica of Our Lady of Aparecida",
        "type": "basilica", "city": "Aparecida", "country": "Brazil",
        "lat": -22.8467, "lng": -45.2275, "founded": "1955–1980",
        "blurb": "The largest Marian basilica in the world, patroness of Brazil.",
        "history": "In 1717 fishermen drew a small dark statue of the Immaculate Conception from the "
        "Paraíba River, after which their nets filled abundantly. Devotion grew into the immense basilica "
        "that today welcomes millions of pilgrims.",
        "relics": ["The statue of Our Lady of Aparecida"],
        "saints": ["St. Frei Galvão (Brazil's first native-born saint)"],
        "miracles": ["The miraculous catch of fish", "Healings attributed to Our Lady of Aparecida"],
        "source_url": "https://www.santuarionacional.com.br/",
    },
    {
        "slug": "westminster-cathedral",
        "name": "Westminster Cathedral",
        "type": "cathedral", "city": "London", "country": "United Kingdom",
        "lat": 51.4964, "lng": -0.1397, "founded": "1895–1903",
        "blurb": "Mother church of Catholic England and Wales, in striking Byzantine style.",
        "history": "The largest Catholic church in England and Wales, built in neo-Byzantine style. It "
        "holds the relics of St. John Southworth, an English martyr.",
        "relics": ["Body of St. John Southworth, martyr"],
        "saints": ["St. John Southworth"],
        "miracles": [],
        "source_url": "https://westminstercathedral.org.uk/",
    },
    {
        "slug": "cologne-cathedral",
        "name": "Cologne Cathedral",
        "type": "cathedral", "city": "Cologne", "country": "Germany",
        "lat": 50.9413, "lng": 6.9583, "founded": "1248–1880",
        "blurb": "Gothic landmark holding the Shrine of the Three Kings (the Magi).",
        "history": "Begun in 1248 to house the relics of the Magi brought from Milan, the cathedral took "
        "over 600 years to complete. Its golden Shrine of the Three Kings is the largest reliquary in the "
        "Western world.",
        "relics": ["The Shrine of the Three Kings (relics of the Magi)"],
        "saints": ["The Three Magi (venerated)"],
        "miracles": [],
        "source_url": "https://www.koelner-dom.de/en/",
    },
    {
        "slug": "guadalupe-la-vang",
        "name": "Basilica of Our Lady of La Vang",
        "type": "apparition", "city": "Quảng Trị", "country": "Vietnam",
        "lat": 16.7464, "lng": 107.0917, "founded": "1798 (apparition)",
        "blurb": "Marian apparition site dear to Vietnamese Catholics amid persecution.",
        "history": "During a violent persecution in 1798, Catholics hiding in the La Vang rainforest "
        "reported an apparition of Our Lady, who comforted them and taught them to use local leaves as "
        "medicine. La Vang became Vietnam's foremost Marian shrine.",
        "relics": [],
        "saints": ["The Vietnamese Martyrs (associated devotion)"],
        "miracles": ["The apparition of Our Lady of La Vang (1798)"],
        "source_url": "https://en.wikipedia.org/wiki/Our_Lady_of_La_Vang",
    },
    {
        "slug": "st-marys-cathedral-sydney",
        "name": "St Mary's Cathedral, Sydney",
        "type": "cathedral", "city": "Sydney", "country": "Australia",
        "lat": -33.8713, "lng": 151.2130, "founded": "1868–1928",
        "blurb": "Mother church of Australian Catholicism, linked to St. Mary MacKillop.",
        "history": "The seat of the Archbishop of Sydney, this English-Gothic cathedral is the spiritual "
        "home of Catholics in Australia and is associated with St. Mary MacKillop, Australia's first saint.",
        "relics": ["Relics associated with St. Mary MacKillop"],
        "saints": ["St. Mary MacKillop"],
        "miracles": ["Two healing miracles approved for St. Mary MacKillop's canonization"],
        "source_url": "https://www.stmaryscathedral.org.au/",
    },
    {
        "slug": "basilica-bom-jesus-goa",
        "name": "Basilica of Bom Jesus, Goa",
        "type": "basilica", "city": "Old Goa", "country": "India",
        "lat": 15.5009, "lng": 73.9116, "founded": "1594–1605",
        "blurb": "Holds the incorrupt body of St. Francis Xavier, apostle of the Indies.",
        "history": "A UNESCO World Heritage church, the Basilica of Bom Jesus enshrines the incorrupt body "
        "of St. Francis Xavier, the great Jesuit missionary to Asia, displayed periodically for veneration.",
        "relics": ["Incorrupt body of St. Francis Xavier"],
        "saints": ["St. Francis Xavier"],
        "miracles": ["The incorruptibility of St. Francis Xavier's body"],
        "source_url": "https://whc.unesco.org/en/list/234/",
    },
]


def _public(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "site_id": doc.get("site_id"),
        "slug": doc.get("slug"),
        "name": doc.get("name"),
        "type": doc.get("type") or "church",
        "city": doc.get("city"),
        "country": doc.get("country"),
        "lat": doc.get("lat"),
        "lng": doc.get("lng"),
        "founded": doc.get("founded"),
        "blurb": doc.get("blurb"),
        "history": doc.get("history"),
        "relics": doc.get("relics") or [],
        "saints": doc.get("saints") or [],
        "miracles": doc.get("miracles") or [],
        "source_url": doc.get("source_url"),
    }


async def _localize(db, items: List[Dict[str, Any]]):
    """Translate string + string-list fields into the request language."""
    import os as _os
    lang = get_lang()
    if lang == "en" or not items:
        return items
    texts: List[str] = []
    # (item_index, field, list_index|-1)
    idx: List[tuple] = []
    str_fields = ["name", "blurb", "history", "city", "country", "founded"]
    list_fields = ["relics", "saints", "miracles"]
    for i, it in enumerate(items):
        for f in str_fields:
            v = it.get(f)
            if isinstance(v, str) and v.strip():
                idx.append((i, f, -1))
                texts.append(v)
        for f in list_fields:
            arr = it.get(f) or []
            for j, v in enumerate(arr):
                if isinstance(v, str) and v.strip():
                    idx.append((i, f, j))
                    texts.append(v)
    if not texts:
        return items
    try:
        from i18n_translate import translate_texts
        tr = await translate_texts(db, _os.environ.get("EMERGENT_LLM_KEY", ""), texts, lang)
        for (i, f, j), t in zip(idx, tr):
            if not (isinstance(t, str) and t.strip()):
                continue
            if j < 0:
                items[i][f] = t
            else:
                items[i][f][j] = t
    except Exception:  # noqa: BLE001
        pass
    return items


async def _seed_if_missing(db) -> int:
    col = db["catholic_sites"]
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    for s in SEED_SITES:
        if await col.find_one({"slug": s["slug"]}, {"_id": 1}):
            continue
        await col.insert_one({"site_id": f"site_{uuid.uuid4().hex[:12]}", **s, "created_at": now})
        inserted += 1
    return inserted


def build_router(db: AsyncIOMotorDatabase, get_current_user, emergent_llm_key: str = "") -> APIRouter:
    router = APIRouter(prefix="/sites", tags=["catholic-sites"])
    col = db["catholic_sites"]

    @router.get("")
    async def list_sites(user=Depends(get_current_user)):
        await _seed_if_missing(db)
        cur = col.find({}, {"_id": 0}).sort([("name", 1)])
        items = [_public(d) async for d in cur]
        # Markers (name/coords/type) localize cheaply; full detail localized on demand.
        await _localize(db, items)
        return {"items": items, "total": len(items)}

    @router.get("/{site_id}")
    async def get_site(site_id: str, user=Depends(get_current_user)):
        doc = await col.find_one({"$or": [{"site_id": site_id}, {"slug": site_id}]}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Site not found")
        item = _public(doc)
        await _localize(db, [item])
        return item

    return router
