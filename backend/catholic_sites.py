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
    # ---- Expanded atlas: more countries across every continent ---- #
    {"slug": "lujan-argentina", "name": "Basilica of Our Lady of Luján", "type": "basilica",
     "city": "Luján", "country": "Argentina", "lat": -34.5709, "lng": -59.1050, "founded": "1887–1935",
     "blurb": "National shrine of Argentina, home of the small image of Our Lady of Luján.",
     "history": "In 1630 a cart carrying a terracotta image of the Immaculate Conception could not move until "
     "the statue was left behind — taken as a sign she wished to remain at Luján, now Argentina's patroness.",
     "relics": ["The image of Our Lady of Luján"], "saints": [],
     "miracles": ["The cart that would not move until the image was left at Luján"],
     "source_url": "https://en.wikipedia.org/wiki/Bas%C3%ADlica_de_Luj%C3%A1n"},
    {"slug": "st-joseph-oratory", "name": "Saint Joseph's Oratory of Mount Royal", "type": "basilica",
     "city": "Montreal", "country": "Canada", "lat": 45.4923, "lng": -73.6177, "founded": "1904–1967",
     "blurb": "Canada's largest church, built through the devotion of St. André Bessette to St. Joseph.",
     "history": "Br. André Bessette, a humble porter, attributed countless healings to St. Joseph; pilgrims "
     "left crutches as testimony. His tomb and preserved heart are venerated here.",
     "relics": ["Tomb of St. André Bessette", "The preserved heart of St. André"],
     "saints": ["St. André Bessette"], "miracles": ["Healings attributed to St. Joseph through St. André"],
     "source_url": "https://www.saint-joseph.org/en/"},
    {"slug": "sainte-anne-de-beaupre", "name": "Sanctuary of Sainte-Anne-de-Beaupré", "type": "shrine",
     "city": "Beaupré, Québec", "country": "Canada", "lat": 47.0224, "lng": -70.9286, "founded": "1658 / 1923",
     "blurb": "A great shrine to St. Anne, mother of Mary, famed for reported healings.",
     "history": "Devotion to St. Anne began with French settlers and Mi'kmaq converts; the basilica holds a "
     "relic of St. Anne and is lined with crutches left by those who were healed.",
     "relics": ["Relic of St. Anne (the Grande Relique)"], "saints": ["St. Anne"],
     "miracles": ["Reported healings at the shrine of St. Anne"],
     "source_url": "https://sanctuairesainteanne.org/en/"},
    {"slug": "las-lajas", "name": "Las Lajas Sanctuary", "type": "shrine",
     "city": "Ipiales", "country": "Colombia", "lat": 0.8056, "lng": -77.5856, "founded": "1916–1949",
     "blurb": "A neo-Gothic church spanning a canyon gorge around a miraculous image on the rock.",
     "history": "Tradition holds that the image of Our Lady of Las Lajas appeared on the canyon wall after a "
     "deaf-mute girl was cured; the church was built bridging the gorge around the rock face.",
     "relics": ["The image of Our Lady of Las Lajas on the rock"], "saints": [],
     "miracles": ["The image said to be imprinted on the rock face", "Reported healings"],
     "source_url": "https://en.wikipedia.org/wiki/Las_Lajas_Sanctuary"},
    {"slug": "santa-rosa-lima", "name": "Sanctuary of St. Rose of Lima", "type": "shrine",
     "city": "Lima", "country": "Peru", "lat": -12.0432, "lng": -77.0282, "founded": "17th century",
     "blurb": "Home of St. Rose of Lima, the first canonized saint of the Americas.",
     "history": "St. Rose lived a life of penance and charity in Lima; her hermitage and the well into which "
     "she threw the key of her penitential chain are venerated by pilgrims.",
     "relics": ["Relics of St. Rose of Lima"], "saints": ["St. Rose of Lima", "St. Martin de Porres (Lima)"],
     "miracles": ["Healings attributed to St. Rose"],
     "source_url": "https://en.wikipedia.org/wiki/Rose_of_Lima"},
    {"slug": "voto-nacional-quito", "name": "Basílica del Voto Nacional", "type": "basilica",
     "city": "Quito", "country": "Ecuador", "lat": -0.2147, "lng": -78.5074, "founded": "1892–1924",
     "blurb": "The largest neo-Gothic basilica in the Americas, consecrated to the Sacred Heart.",
     "history": "Built as a national vow consecrating Ecuador to the Sacred Heart of Jesus, its gargoyles "
     "depict native Ecuadorian animals in place of traditional figures.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Basilica_of_the_National_Vow"},
    {"slug": "copacabana-bolivia", "name": "Basilica of Our Lady of Copacabana", "type": "basilica",
     "city": "Copacabana", "country": "Bolivia", "lat": -16.1667, "lng": -69.0863, "founded": "1601–1820",
     "blurb": "Shrine of Our Lady of Copacabana, patroness of Bolivia, on the shore of Lake Titicaca.",
     "history": "The venerated statue was carved by the indigenous artist Francisco Tito Yupanqui in 1583; "
     "Our Lady of Copacabana became patroness of Bolivia and Peru.",
     "relics": ["The statue of Our Lady of Copacabana"], "saints": [],
     "miracles": ["Healings attributed to Our Lady of Copacabana"],
     "source_url": "https://en.wikipedia.org/wiki/Our_Lady_of_Copacabana"},
    {"slug": "coromoto-venezuela", "name": "Basilica of Our Lady of Coromoto", "type": "apparition",
     "city": "Guanare", "country": "Venezuela", "lat": 9.0431, "lng": -69.7419, "founded": "apparition 1652",
     "blurb": "Built where Our Lady appeared to the Coromoto people; patroness of Venezuela.",
     "history": "In 1652 the Virgin appeared to the chief of the Coromoto, leaving a tiny image on a small "
     "relic still venerated today. She was declared patroness of Venezuela.",
     "relics": ["The tiny relic-image of Our Lady of Coromoto"], "saints": [],
     "miracles": ["The apparition of Our Lady of Coromoto"],
     "source_url": "https://en.wikipedia.org/wiki/Our_Lady_of_Coromoto"},
    {"slug": "esquipulas", "name": "Basilica of Esquipulas (Black Christ)", "type": "basilica",
     "city": "Esquipulas", "country": "Guatemala", "lat": 14.5667, "lng": -89.3500, "founded": "1735–1758",
     "blurb": "Home of the venerated Black Christ crucifix, drawing millions of Central American pilgrims.",
     "history": "The dark-wood crucifix carved in 1594 became a great pilgrimage centre; Esquipulas is called "
     "the spiritual capital of Central America.",
     "relics": ["The Black Christ (Cristo Negro) crucifix"], "saints": [],
     "miracles": ["Healings attributed to the Black Christ of Esquipulas"],
     "source_url": "https://en.wikipedia.org/wiki/Esquipulas"},
    {"slug": "el-cobre-cuba", "name": "Basilica of Our Lady of Charity of El Cobre", "type": "basilica",
     "city": "El Cobre", "country": "Cuba", "lat": 20.0447, "lng": -75.9389, "founded": "1926",
     "blurb": "National shrine of Cuba, home of 'La Caridad', patroness of the island.",
     "history": "Tradition holds the statue was found around 1612 floating on the sea by 'the three Juans', "
     "her clothes perfectly dry. Our Lady of Charity is patroness of Cuba.",
     "relics": ["The statue of Our Lady of Charity (La Caridad del Cobre)"], "saints": [],
     "miracles": ["The statue found floating and dry at sea"],
     "source_url": "https://en.wikipedia.org/wiki/Our_Lady_of_Charity"},
    {"slug": "higuey-dominican", "name": "Basilica of Our Lady of Altagracia", "type": "basilica",
     "city": "Higüey", "country": "Dominican Republic", "lat": 18.6160, "lng": -68.7080, "founded": "1971",
     "blurb": "The spiritual heart of the Dominican Republic, honouring Our Lady of Altagracia.",
     "history": "The small image of Our Lady of Altagracia, brought by early Spanish settlers, is the "
     "protectress of the Dominican people, celebrated each 21 January.",
     "relics": ["The image of Our Lady of Altagracia"], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Our_Lady_of_Altagracia"},
    {"slug": "caacupe-paraguay", "name": "Basilica of Our Lady of Caacupé", "type": "basilica",
     "city": "Caacupé", "country": "Paraguay", "lat": -25.3866, "lng": -57.1410, "founded": "1945–1980",
     "blurb": "Shrine of Our Lady of the Miracles of Caacupé, patroness of Paraguay.",
     "history": "Tradition tells of a convert who carved the image from a tree behind which he hid from "
     "enemies; the statue survived a great flood, and Caacupé became the national shrine.",
     "relics": ["The image of Our Lady of Caacupé"], "saints": [],
     "miracles": ["The image's survival of the flood of Tobatí"],
     "source_url": "https://en.wikipedia.org/wiki/Our_Lady_of_Caacup%C3%A9"},
    {"slug": "los-angeles-cartago", "name": "Basilica of Our Lady of the Angels", "type": "basilica",
     "city": "Cartago", "country": "Costa Rica", "lat": 9.8644, "lng": -83.9186, "founded": "1639 / 1939",
     "blurb": "Home of 'La Negrita', the tiny stone image patroness of Costa Rica.",
     "history": "A small dark stone statue found in 1635 repeatedly returned to the same spot when moved; the "
     "basilica was built over the rock, and a spring there is associated with healings.",
     "relics": ["La Negrita (stone image of Our Lady of the Angels)"], "saints": [],
     "miracles": ["The image returning to its found-spot", "The healing spring at the basilica"],
     "source_url": "https://en.wikipedia.org/wiki/Our_Lady_of_the_Angels_Basilica"},
    {"slug": "divine-mercy-stockbridge", "name": "National Shrine of The Divine Mercy", "type": "shrine",
     "city": "Stockbridge, MA", "country": "United States", "lat": 42.2853, "lng": -73.3110, "founded": "1950s",
     "blurb": "Centre of the Divine Mercy devotion revealed to St. Faustina Kowalska.",
     "history": "Run by the Marian Fathers, the shrine spreads the message of Divine Mercy given to St. "
     "Faustina, drawing pilgrims especially on Divine Mercy Sunday.",
     "relics": ["Relic of St. Faustina Kowalska"], "saints": ["St. Faustina Kowalska"], "miracles": [],
     "source_url": "https://www.thedivinemercy.org/"},
    {"slug": "san-juan-capistrano", "name": "Mission San Juan Capistrano", "type": "church",
     "city": "California", "country": "United States", "lat": 33.5016, "lng": -117.6628, "founded": "1776",
     "blurb": "A Spanish mission founded by St. Junípero Serra, 'Jewel of the Missions'.",
     "history": "Founded in 1776 by St. Junípero Serra, the mission's Serra Chapel is the oldest building in "
     "California still in use and where the saint himself offered Mass.",
     "relics": [], "saints": ["St. Junípero Serra"], "miracles": [],
     "source_url": "https://www.missionsjc.com/"},
    {"slug": "montserrat", "name": "Santa Maria de Montserrat Abbey", "type": "monastery",
     "city": "Montserrat", "country": "Spain", "lat": 41.5934, "lng": 1.8357, "founded": "11th century",
     "blurb": "Benedictine abbey in the mountains, home of 'La Moreneta', the Black Madonna of Montserrat.",
     "history": "Set amid dramatic peaks, the abbey enshrines the venerated dark statue of the Virgin and is "
     "a centre of Catalan spirituality; St. Ignatius laid down his sword here before his conversion.",
     "relics": ["The statue of the Virgin of Montserrat (La Moreneta)"],
     "saints": ["St. Ignatius of Loyola (linked to his conversion)"], "miracles": [],
     "source_url": "https://www.montserratvisita.com/en/"},
    {"slug": "pilar-zaragoza", "name": "Basilica of Our Lady of the Pillar", "type": "basilica",
     "city": "Zaragoza", "country": "Spain", "lat": 41.6566, "lng": -0.8779, "founded": "1681–1872",
     "blurb": "Built on the spot where Our Lady appeared to St. James upon a pillar of jasper.",
     "history": "Tradition holds that in AD 40 the Virgin Mary — still living in Jerusalem — appeared to St. "
     "James in Zaragoza standing on a pillar, which is enshrined here. The 1936 unexploded bombs are displayed.",
     "relics": ["The Holy Pillar (column of jasper)"], "saints": ["St. James the Greater"],
     "miracles": ["The apparition of Our Lady of the Pillar", "The Miracle of Calanda (a restored leg, 1640)"],
     "source_url": "https://www.basilicadelpilar.es/"},
    {"slug": "rue-du-bac", "name": "Chapel of Our Lady of the Miraculous Medal", "type": "apparition",
     "city": "Paris", "country": "France", "lat": 48.8514, "lng": 2.3245, "founded": "apparitions 1830",
     "blurb": "Where Our Lady gave St. Catherine Labouré the design of the Miraculous Medal.",
     "history": "In 1830 the Virgin appeared to St. Catherine Labouré at the Rue du Bac, asking that a medal "
     "be struck. The incorrupt body of St. Catherine rests beneath the altar.",
     "relics": ["Incorrupt body of St. Catherine Labouré", "Heart of St. Vincent de Paul (nearby)"],
     "saints": ["St. Catherine Labouré"],
     "miracles": ["The apparitions of the Miraculous Medal"],
     "source_url": "https://www.chapellenotredamedelamedaillemiraculeuse.com/en/"},
    {"slug": "mont-saint-michel", "name": "Abbey of Mont-Saint-Michel", "type": "monastery",
     "city": "Normandy", "country": "France", "lat": 48.6361, "lng": -1.5115, "founded": "8th century",
     "blurb": "A Benedictine abbey crowning a tidal island, dedicated to St. Michael the Archangel.",
     "history": "Founded after St. Michael reportedly appeared to St. Aubert of Avranches in 708, the abbey "
     "rises dramatically from the bay and was a great medieval pilgrimage site.",
     "relics": [], "saints": ["St. Michael the Archangel (dedication)", "St. Aubert"], "miracles": [],
     "source_url": "https://www.ot-montsaintmichel.com/en/"},
    {"slug": "la-salette", "name": "Sanctuary of Our Lady of La Salette", "type": "apparition",
     "city": "La Salette-Fallavaux", "country": "France", "lat": 44.8589, "lng": 5.9806, "founded": "apparition 1846",
     "blurb": "Mountain shrine where Our Lady, weeping, appeared to two shepherd children in 1846.",
     "history": "On 19 September 1846 the Virgin appeared in tears to Mélanie and Maximin, calling for "
     "conversion and the keeping of Sunday. The apparition was approved in 1851.",
     "relics": [], "saints": [], "miracles": ["The weeping apparition of Our Lady of La Salette"],
     "source_url": "https://www.lasalette.cef.fr/"},
    {"slug": "mariazell", "name": "Mariazell Basilica", "type": "basilica",
     "city": "Mariazell", "country": "Austria", "lat": 47.7717, "lng": 15.3186, "founded": "12th century",
     "blurb": "'Magna Mater Austriae' — the most important Marian shrine of Austria and Central Europe.",
     "history": "Founded by a Benedictine monk in 1157, its small lime-wood statue 'Mariazell' draws "
     "pilgrims from Austria, Hungary and beyond as a shared mother of the region.",
     "relics": ["The 'Magna Mater Austriae' statue"], "saints": [],
     "miracles": ["Healings long attributed to Our Lady of Mariazell"],
     "source_url": "https://www.basilika-mariazell.at/"},
    {"slug": "altotting", "name": "Shrine of Our Lady of Altötting", "type": "shrine",
     "city": "Altötting", "country": "Germany", "lat": 48.2270, "lng": 12.6760, "founded": "medieval",
     "blurb": "The 'Heart of Bavaria', home of a Black Madonna and a national German Marian shrine.",
     "history": "The Chapel of Grace enshrines a venerated Black Madonna; the hearts of Bavarian kings and "
     "of Pope Benedict XVI's homeland devotion are tied to this place.",
     "relics": ["The Black Madonna of Altötting"], "saints": ["St. Conrad of Parzham (lived nearby)"],
     "miracles": ["Healings attributed to Our Lady of Altötting"],
     "source_url": "https://www.altoetting.de/"},
    {"slug": "einsiedeln", "name": "Einsiedeln Abbey", "type": "monastery",
     "city": "Einsiedeln", "country": "Switzerland", "lat": 47.1267, "lng": 8.7522, "founded": "934",
     "blurb": "A great Benedictine abbey enshrining the Black Madonna of Einsiedeln.",
     "history": "Founded on the hermitage of St. Meinrad, the abbey's Chapel of Grace holds a venerated "
     "Black Madonna and lies on the Camino and pilgrim routes to Santiago.",
     "relics": ["The Black Madonna of Einsiedeln"], "saints": ["St. Meinrad"], "miracles": [],
     "source_url": "https://www.kloster-einsiedeln.ch/"},
    {"slug": "esztergom", "name": "Esztergom Basilica", "type": "basilica",
     "city": "Esztergom", "country": "Hungary", "lat": 47.7989, "lng": 18.7361, "founded": "1822–1869",
     "blurb": "The largest church in Hungary and seat of the Hungarian primate.",
     "history": "Built on Castle Hill above the Danube, it stands where St. Stephen, first king of Hungary, "
     "was crowned. Its Bakócz Chapel is a Renaissance masterpiece.",
     "relics": [], "saints": ["St. Stephen of Hungary (connected)", "St. Adalbert (dedication)"], "miracles": [],
     "source_url": "https://www.bazilika-esztergom.hu/en"},
    {"slug": "infant-jesus-prague", "name": "Church of Our Lady Victorious (Infant of Prague)", "type": "church",
     "city": "Prague", "country": "Czechia", "lat": 50.0863, "lng": 14.4036, "founded": "1611",
     "blurb": "Home of the world-famous wax statue of the Infant Jesus of Prague.",
     "history": "A small wax image of the Child Jesus, given to the Carmelites in 1628, became a focus of "
     "devotion and countless reported favours, venerated worldwide.",
     "relics": ["The statue of the Infant Jesus of Prague"], "saints": [],
     "miracles": ["Favours attributed to the Infant of Prague"],
     "source_url": "https://www.pragjesu.cz/en/"},
    {"slug": "marija-bistrica", "name": "Shrine of Our Lady of Bistrica", "type": "shrine",
     "city": "Marija Bistrica", "country": "Croatia", "lat": 46.0167, "lng": 16.1167, "founded": "16th century",
     "blurb": "The national Marian shrine of Croatia, home of a Black Madonna.",
     "history": "A wooden Black Madonna hidden during Ottoman raids was rediscovered intact; the shrine "
     "became Croatia's national sanctuary, where John Paul II beatified Bl. Alojzije Stepinac.",
     "relics": ["The Black Madonna of Bistrica"], "saints": ["Bl. Alojzije Stepinac (beatified here)"], "miracles": [],
     "source_url": "https://www.svetiste-mbistrica.hr/"},
    {"slug": "sastin-slovakia", "name": "Basilica of the Seven Sorrows", "type": "basilica",
     "city": "Šaštín", "country": "Slovakia", "lat": 48.6386, "lng": 17.1469, "founded": "1736–1764",
     "blurb": "National shrine of Slovakia, honouring Our Lady of Sorrows, patroness of the nation.",
     "history": "Built around a venerated pietà, Šaštín is Slovakia's foremost pilgrimage site; "
     "Pope Francis prayed here in 2021.",
     "relics": ["The pietà of Our Lady of Sorrows"], "saints": [], "miracles": [],
     "source_url": "https://www.bazilika.sk/"},
    {"slug": "gate-of-dawn", "name": "Chapel of the Gate of Dawn", "type": "shrine",
     "city": "Vilnius", "country": "Lithuania", "lat": 54.6731, "lng": 25.2897, "founded": "16th century",
     "blurb": "Home of the miraculous icon of Our Lady of the Gate of Dawn, Mother of Mercy.",
     "history": "Set above the last surviving city gate of Vilnius, the gilded icon of the Mother of Mercy is "
     "revered by Catholics and Orthodox alike across the Baltic and Poland.",
     "relics": ["The icon of Our Lady of the Gate of Dawn"], "saints": [],
     "miracles": ["Healings attributed to the Mother of Mercy"],
     "source_url": "https://en.wikipedia.org/wiki/Gate_of_Dawn"},
    {"slug": "hill-of-crosses", "name": "Hill of Crosses", "type": "shrine",
     "city": "Šiauliai", "country": "Lithuania", "lat": 56.0153, "lng": 23.4169, "founded": "19th century",
     "blurb": "A hill bearing hundreds of thousands of crosses — a symbol of faith under persecution.",
     "history": "Lithuanians planted crosses here in defiance of Tsarist and Soviet rule; though bulldozed "
     "repeatedly, the crosses always returned. St. John Paul II visited in 1993.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Hill_of_Crosses"},
    {"slug": "servatius-maastricht", "name": "Basilica of St. Servatius", "type": "basilica",
     "city": "Maastricht", "country": "Netherlands", "lat": 50.8492, "lng": 5.6880, "founded": "6th century origins",
     "blurb": "The oldest church in the Netherlands, built over the tomb of St. Servatius.",
     "history": "St. Servatius, first bishop in the Low Countries, was buried here in 384; the treasury "
     "holds remarkable medieval reliquaries displayed during the septennial pilgrimage.",
     "relics": ["Tomb and relics of St. Servatius"], "saints": ["St. Servatius"], "miracles": [],
     "source_url": "https://www.sintservaas.nl/"},
    {"slug": "beauraing", "name": "Shrine of Our Lady of Beauraing", "type": "apparition",
     "city": "Beauraing", "country": "Belgium", "lat": 50.1100, "lng": 4.9560, "founded": "apparitions 1932–33",
     "blurb": "Where Our Lady, the 'Virgin with the Golden Heart', appeared to five children.",
     "history": "Between 1932 and 1933 the Virgin appeared 33 times to five children, showing her golden "
     "heart and calling for prayer. The apparitions were approved in 1949.",
     "relics": [], "saints": [], "miracles": ["The apparitions of Our Lady of Beauraing"],
     "source_url": "https://www.beauraing.be/"},
    {"slug": "st-johns-valletta", "name": "St. John's Co-Cathedral", "type": "cathedral",
     "city": "Valletta", "country": "Malta", "lat": 35.8979, "lng": 14.5125, "founded": "1572–1577",
     "blurb": "Baroque jewel of the Knights of Malta, dedicated to St. John the Baptist.",
     "history": "Built by the Knights Hospitaller, its opulent interior holds Caravaggio's masterpiece 'The "
     "Beheading of St. John the Baptist', the only work the artist ever signed.",
     "relics": [], "saints": ["St. John the Baptist (dedication)"], "miracles": [],
     "source_url": "https://www.stjohnscocathedral.com/"},
    {"slug": "walsingham", "name": "Shrine of Our Lady of Walsingham", "type": "shrine",
     "city": "Walsingham", "country": "United Kingdom", "lat": 52.8939, "lng": 0.8758, "founded": "1061 / restored 1934",
     "blurb": "'England's Nazareth' — a medieval Holy House shrine restored in the 20th century.",
     "history": "Founded after a noblewoman's vision in 1061 directed her to build a replica of the Holy "
     "House of Nazareth, Walsingham was England's premier Marian shrine until the Reformation, now restored.",
     "relics": ["The image of Our Lady of Walsingham"], "saints": [], "miracles": [],
     "source_url": "https://www.walsingham.org.uk/"},
    {"slug": "nidaros-trondheim", "name": "Nidaros Cathedral", "type": "cathedral",
     "city": "Trondheim", "country": "Norway", "lat": 63.4269, "lng": 10.3969, "founded": "1070–1300",
     "blurb": "Built over the tomb of St. Olav, the great medieval pilgrim goal of the north.",
     "history": "Norway's national sanctuary rose over the burial place of St. Olav Haraldsson, king and "
     "martyr; it was the destination of pilgrims along the St. Olav Ways.",
     "relics": ["Burial site of St. Olav"], "saints": ["St. Olav of Norway"], "miracles": [],
     "source_url": "https://www.nidarosdomen.no/en"},
    {"slug": "house-of-virgin-ephesus", "name": "House of the Virgin Mary", "type": "shrine",
     "city": "Ephesus (Selçuk)", "country": "Turkey", "lat": 37.9117, "lng": 27.3339, "founded": "1st century (tradition)",
     "blurb": "A stone house revered as the home where the Virgin Mary spent her final years.",
     "history": "Discovered through the visions of Bl. Anne Catherine Emmerich, the small house near Ephesus "
     "is honoured as Mary's last dwelling and has been visited by several popes.",
     "relics": [], "saints": ["The Blessed Virgin Mary", "St. John the Apostle (tradition)"], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/House_of_the_Virgin_Mary"},
    {"slug": "our-lady-of-lebanon", "name": "Our Lady of Lebanon", "type": "shrine",
     "city": "Harissa", "country": "Lebanon", "lat": 33.9831, "lng": 35.6517, "founded": "1908",
     "blurb": "A great white statue of the Virgin overlooking the Bay of Jounieh, patroness of Lebanon.",
     "history": "Crowning a hill above Jounieh, the bronze statue of Our Lady of Lebanon is a unifying "
     "symbol of faith for the country, visited by Christians and Muslims alike.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Our_Lady_of_Lebanon"},
    {"slug": "st-charbel-annaya", "name": "Monastery of St. Maron, Annaya", "type": "monastery",
     "city": "Annaya", "country": "Lebanon", "lat": 34.1247, "lng": 35.7339, "founded": "19th century",
     "blurb": "Resting place of St. Charbel Makhlouf, the Maronite hermit of many miracles.",
     "history": "St. Charbel lived as a hermit of intense prayer and penance; after his death in 1898 his "
     "tomb radiated light and his body exuded a fluid, with thousands of healings reported.",
     "relics": ["Tomb of St. Charbel Makhlouf"], "saints": ["St. Charbel Makhlouf"],
     "miracles": ["Light over his tomb", "Thousands of documented healings"],
     "source_url": "https://saintcharbel-annaya.com/en/"},
    {"slug": "sheshan-shanghai", "name": "Basilica of Our Lady of Sheshan", "type": "basilica",
     "city": "Shanghai", "country": "China", "lat": 31.0958, "lng": 121.1939, "founded": "1925–1935",
     "blurb": "The largest church in East Asia, atop Sheshan hill, honouring Our Lady, Help of Christians.",
     "history": "A great pilgrimage church crowning Sheshan hill; Pope Benedict XVI composed a special "
     "prayer to Our Lady of Sheshan for the Church in China, prayed each 24 May.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Basilica_of_Our_Lady_of_Sheshan"},
    {"slug": "myeongdong-seoul", "name": "Myeongdong Cathedral", "type": "cathedral",
     "city": "Seoul", "country": "South Korea", "lat": 37.5634, "lng": 126.9874, "founded": "1898",
     "blurb": "Cradle of Korean Catholicism, honouring the Korean Martyrs.",
     "history": "Built on the site of the first Korean Catholic community, the cathedral enshrines relics of "
     "Korean martyrs and was a refuge for democracy and human dignity in modern times.",
     "relics": ["Relics of Korean Martyrs"], "saints": ["St. Andrew Kim Taegŏn and the Korean Martyrs"], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Myeongdong_Cathedral"},
    {"slug": "oura-nagasaki", "name": "Ōura Cathedral", "type": "cathedral",
     "city": "Nagasaki", "country": "Japan", "lat": 32.7339, "lng": 129.8703, "founded": "1864",
     "blurb": "Dedicated to the Twenty-Six Martyrs of Japan, scene of the 'Discovery of Hidden Christians'.",
     "history": "Soon after it was built, hidden Christians who had kept the faith in secret for 250 years "
     "revealed themselves to the priest here in 1865 — a moment called a 'miracle of the Orient'.",
     "relics": [], "saints": ["St. Paul Miki and the Twenty-Six Martyrs of Japan"],
     "miracles": ["The rediscovery of the Hidden Christians (1865)"],
     "source_url": "https://nagasaki-oura-church.jp/en"},
    {"slug": "madhu-srilanka", "name": "Shrine of Our Lady of Madhu", "type": "shrine",
     "city": "Mannar", "country": "Sri Lanka", "lat": 8.8270, "lng": 80.1980, "founded": "1670s",
     "blurb": "A 400-year Marian shrine, refuge of all communities through Sri Lanka's conflicts.",
     "history": "Sheltering Catholics fleeing persecution, the shrine of Our Lady of Madhu became a symbol "
     "of protection — its soil long believed to guard against snakebite — and a place of national pilgrimage.",
     "relics": ["The statue of Our Lady of Madhu"], "saints": [],
     "miracles": ["Reported protection from snakebite at the shrine"],
     "source_url": "https://en.wikipedia.org/wiki/Madhu_Church"},
    {"slug": "assumption-bangkok", "name": "Assumption Cathedral", "type": "cathedral",
     "city": "Bangkok", "country": "Thailand", "lat": 13.7250, "lng": 100.5163, "founded": "1809 / 1918",
     "blurb": "The principal Catholic church of Thailand, by the Chao Phraya River.",
     "history": "A romanesque cathedral of red brick, it is the seat of the Archbishop of Bangkok and was "
     "visited by both St. John Paul II and Pope Francis.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Assumption_Cathedral,_Bangkok"},
    {"slug": "jakarta-cathedral", "name": "Jakarta Cathedral", "type": "cathedral",
     "city": "Jakarta", "country": "Indonesia", "lat": -6.1696, "lng": 106.8324, "founded": "1901",
     "blurb": "Neo-Gothic cathedral standing beside the great mosque as a sign of harmony.",
     "history": "The Church of Our Lady of the Assumption faces the Istiqlal Mosque across the square; the "
     "two are linked by a 'Tunnel of Friendship' symbolising interreligious respect.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Jakarta_Cathedral"},
    {"slug": "yamoussoukro", "name": "Basilica of Our Lady of Peace", "type": "basilica",
     "city": "Yamoussoukro", "country": "Ivory Coast", "lat": 6.8108, "lng": -5.2986, "founded": "1985–1989",
     "blurb": "The largest church in the world by area, consecrated by St. John Paul II.",
     "history": "Modelled on St. Peter's, this vast basilica on the savannah was consecrated in 1990 and is "
     "recognised by Guinness World Records as the largest church building on earth.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Basilica_of_Our_Lady_of_Peace_of_Yamoussoukro"},
    {"slug": "uganda-martyrs", "name": "Basilica of the Uganda Martyrs, Namugongo", "type": "basilica",
     "city": "Namugongo", "country": "Uganda", "lat": 0.3897, "lng": 32.6680, "founded": "1968–1975",
     "blurb": "Built where St. Charles Lwanga and companions were martyred for the faith.",
     "history": "On this site in 1886 young Christian pages were burned alive for refusing to renounce "
     "Christ; millions gather each 3 June, making it Africa's greatest pilgrimage.",
     "relics": ["Relics of the Uganda Martyrs"], "saints": ["St. Charles Lwanga and the Uganda Martyrs"],
     "miracles": [], "source_url": "https://en.wikipedia.org/wiki/Uganda_Martyrs"},
    {"slug": "holy-family-nairobi", "name": "Holy Family Basilica", "type": "basilica",
     "city": "Nairobi", "country": "Kenya", "lat": -1.2864, "lng": 36.8211, "founded": "1960s",
     "blurb": "The cathedral basilica at the heart of Nairobi and the Kenyan Church.",
     "history": "Seat of the Archdiocese of Nairobi, the modern basilica serves as a spiritual centre for "
     "Catholics across Kenya and East Africa.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Holy_Family_Basilica,_Nairobi"},
    {"slug": "notre-dame-kinshasa", "name": "Notre-Dame du Congo Cathedral", "type": "cathedral",
     "city": "Kinshasa", "country": "DR Congo", "lat": -4.3360, "lng": 15.3210, "founded": "1947",
     "blurb": "Mother church of the vast and fervent Congolese Catholic Church.",
     "history": "Cathedral of the Archdiocese of Kinshasa, it is a centre of the lively Congolese liturgical "
     "tradition, including the distinctive Congolese Rite of the Mass.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Notre-Dame_du_Congo_Cathedral"},
    {"slug": "owerri-cathedral", "name": "Maria Assumpta Cathedral", "type": "cathedral",
     "city": "Owerri", "country": "Nigeria", "lat": 5.4836, "lng": 7.0333, "founded": "1980s",
     "blurb": "A major cathedral of Nigeria's vibrant and growing Catholic community.",
     "history": "Seat of the Archdiocese of Owerri in southeastern Nigeria, it serves one of the most "
     "Catholic regions of Africa, rich in vocations.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Maria_Assumpta_Cathedral"},
    {"slug": "emmanuel-durban", "name": "Emmanuel Cathedral", "type": "cathedral",
     "city": "Durban", "country": "South Africa", "lat": -29.8616, "lng": 31.0203, "founded": "1902–1904",
     "blurb": "One of the largest cathedrals in southern Africa, in the heart of Durban.",
     "history": "Seat of the Archdiocese of Durban, the Gothic-revival cathedral has long served a diverse "
     "urban congregation and works of charity in the city.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Emmanuel_Cathedral,_Durban"},
    {"slug": "st-patrick-auckland", "name": "St Patrick's Cathedral, Auckland", "type": "cathedral",
     "city": "Auckland", "country": "New Zealand", "lat": -36.8447, "lng": 174.7676, "founded": "1841 / 1885",
     "blurb": "The mother church of the Catholic Church in New Zealand's largest city.",
     "history": "One of the oldest Catholic churches in New Zealand, the Gothic-revival cathedral is the "
     "seat of the Bishop of Auckland.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://www.stpatricks.org.nz/"},
    # ---- Churches under persecution (highlighted) ---- #
    {"slug": "our-lady-salvation-baghdad", "name": "Our Lady of Salvation Cathedral", "type": "cathedral",
     "city": "Baghdad", "country": "Iraq", "lat": 33.3152, "lng": 44.3661, "founded": "1968",
     "blurb": "Syriac Catholic cathedral, site of the 2010 massacre, a symbol of Iraq's suffering Church.",
     "history": "On 31 October 2010, gunmen attacked during Mass, killing 58 worshippers and priests. The "
     "martyrs' cause for beatification is open; the church remains a sign of faith amid persecution.",
     "relics": [], "saints": ["The 2010 Martyrs of Baghdad (cause open)"], "miracles": [],
     "persecuted": True,
     "persecution_note": "Iraq's Christians have been devastated by war and terrorism; this cathedral itself was the site of a 2010 massacre. Pray for the persecuted Church in Iraq.",
     "source_url": "https://en.wikipedia.org/wiki/Our_Lady_of_Salvation_Church,_Baghdad"},
    {"slug": "al-tahira-qaraqosh", "name": "Al-Tahira (Immaculate Conception) Church", "type": "church",
     "city": "Qaraqosh", "country": "Iraq", "lat": 36.2700, "lng": 43.3800, "founded": "1932 / restored 2021",
     "blurb": "The largest church in Iraq, burned by ISIS in 2014 and since restored.",
     "history": "When ISIS overran the Nineveh Plains in 2014, this great church was desecrated and burned. "
     "After the town's liberation it was restored, and Pope Francis prayed here during his 2021 visit to Iraq.",
     "relics": [], "saints": [], "miracles": [],
     "persecuted": True,
     "persecution_note": "Desecrated and burned by ISIS in 2014; the Christians of the Nineveh Plains were driven from their ancient homeland. Pray for their return and protection.",
     "source_url": "https://en.wikipedia.org/wiki/Al-Tahira_Church,_Bakhdida"},
    {"slug": "st-thecla-maaloula", "name": "Monastery of St. Thecla (Mar Takla)", "type": "monastery",
     "city": "Maaloula", "country": "Syria", "lat": 33.8463, "lng": 36.5447, "founded": "ancient",
     "blurb": "An ancient shrine in one of the last towns where Aramaic, the language of Jesus, is still spoken.",
     "history": "Honouring St. Thecla, disciple of St. Paul, the monastery was attacked in 2013 and its nuns "
     "abducted (later freed). Maaloula remains a fragile witness of Christianity's earliest days.",
     "relics": ["Shrine of St. Thecla"], "saints": ["St. Thecla"], "miracles": [],
     "persecuted": True,
     "persecution_note": "Attacked during Syria's war; its nuns were abducted in 2013. Pray for Syria's ancient Christian communities.",
     "source_url": "https://en.wikipedia.org/wiki/Mar_Takla"},
    {"slug": "owo-nigeria", "name": "St. Francis Xavier Catholic Church, Owo", "type": "church",
     "city": "Owo", "country": "Nigeria", "lat": 7.1962, "lng": 5.5870, "founded": "20th century",
     "blurb": "Site of the 2022 Pentecost Sunday massacre, a wound on Nigeria's vibrant Church.",
     "history": "On Pentecost Sunday 2022, gunmen attacked the congregation during Mass, killing dozens of "
     "worshippers. It stands as a memorial of the suffering of Nigerian Christians.",
     "relics": [], "saints": [], "miracles": [],
     "persecuted": True,
     "persecution_note": "Nigerian Christians face frequent deadly attacks; this parish suffered a massacre on Pentecost 2022. Pray for Nigeria's persecuted faithful.",
     "source_url": "https://en.wikipedia.org/wiki/Owo_church_massacre"},
    {"slug": "managua-cathedral", "name": "Metropolitan Cathedral of Managua", "type": "cathedral",
     "city": "Managua", "country": "Nicaragua", "lat": 12.1500, "lng": -86.2735, "founded": "1993",
     "blurb": "Seat of a Church enduring severe state repression in Nicaragua.",
     "history": "The distinctive domed cathedral is the centre of a Church whose bishops, priests and "
     "faithful have faced exile, imprisonment and the suppression of processions under the government.",
     "relics": [], "saints": [], "miracles": [],
     "persecuted": True,
     "persecution_note": "Nicaragua's Catholic Church faces intense state persecution — clergy exiled or jailed, processions banned. Pray for the Church in Nicaragua.",
     "source_url": "https://en.wikipedia.org/wiki/Metropolitan_Cathedral_of_Managua"},
    {"slug": "sacred-heart-lahore", "name": "Sacred Heart Cathedral, Lahore", "type": "cathedral",
     "city": "Lahore", "country": "Pakistan", "lat": 31.5600, "lng": 74.3300, "founded": "1907",
     "blurb": "A mother church of Pakistan's small, often-threatened Christian minority.",
     "history": "One of the largest churches in Pakistan, it serves a faithful community that endures "
     "blasphemy accusations, mob violence and church bombings with remarkable courage.",
     "relics": [], "saints": [], "miracles": [],
     "persecuted": True,
     "persecution_note": "Pakistan's Christians face blasphemy laws, mob violence and church attacks. Pray for their safety and freedom.",
     "source_url": "https://en.wikipedia.org/wiki/Sacred_Heart_Cathedral,_Lahore"},
    # ---- More churches around the world ---- #
    {"slug": "st-patricks-nyc", "name": "St. Patrick's Cathedral", "type": "cathedral",
     "city": "New York", "country": "United States", "lat": 40.7585, "lng": -73.9759, "founded": "1858–1878",
     "blurb": "The neo-Gothic seat of the Archdiocese of New York on Fifth Avenue.",
     "history": "A landmark of American Catholicism, it holds the remains of New York's bishops and the relics "
     "of St. Elizabeth Ann Seton and St. Frances Cabrini in its altars.",
     "relics": ["Relics of St. Elizabeth Ann Seton & St. Frances Cabrini"],
     "saints": ["St. Elizabeth Ann Seton", "St. Frances Xavier Cabrini"], "miracles": [],
     "source_url": "https://saintpatrickscathedral.org/"},
    {"slug": "metropolitan-cathedral-mexico", "name": "Mexico City Metropolitan Cathedral", "type": "cathedral",
     "city": "Mexico City", "country": "Mexico", "lat": 19.4341, "lng": -99.1330, "founded": "1573–1813",
     "blurb": "The oldest and largest cathedral in the Americas, on the great square of Mexico City.",
     "history": "Built over two centuries atop the former Aztec sacred precinct, it blends Renaissance, "
     "Baroque and Neoclassical styles and is the heart of Mexican Catholic life.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Mexico_City_Metropolitan_Cathedral"},
    {"slug": "sacre-coeur", "name": "Basilica of the Sacred Heart (Sacré-Cœur)", "type": "basilica",
     "city": "Paris", "country": "France", "lat": 48.8867, "lng": 2.3431, "founded": "1875–1914",
     "blurb": "Atop Montmartre, a basilica of perpetual adoration of the Sacred Heart since 1885.",
     "history": "Built as a national act of penance and hope, the white-domed basilica has hosted continuous "
     "Eucharistic adoration, day and night, for well over a century.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://www.sacre-coeur-montmartre.com/english/"},
    {"slug": "st-vitus-prague", "name": "St. Vitus Cathedral", "type": "cathedral",
     "city": "Prague", "country": "Czechia", "lat": 50.0909, "lng": 14.4006, "founded": "1344–1929",
     "blurb": "The great cathedral within Prague Castle, holding Bohemia's holy relics.",
     "history": "Burial place of Bohemian kings and saints, it enshrines the tomb of St. Wenceslaus and the "
     "relics of St. John of Nepomuk in a silver tomb.",
     "relics": ["Tomb of St. Wenceslaus", "Tomb of St. John of Nepomuk"],
     "saints": ["St. Wenceslaus", "St. John of Nepomuk", "St. Adalbert"], "miracles": [],
     "source_url": "https://www.katedralasvatehovita.cz/en"},
    {"slug": "milan-duomo", "name": "Milan Cathedral (Duomo)", "type": "cathedral",
     "city": "Milan", "country": "Italy", "lat": 45.4642, "lng": 9.1900, "founded": "1386–1965",
     "blurb": "The vast Gothic Duomo, guarding a Holy Nail of the Crucifixion.",
     "history": "Crowned with countless spires and statues, the cathedral preserves a relic believed to be a "
     "Nail from the Cross, raised yearly in the Rite of the Nivola begun by St. Charles Borromeo.",
     "relics": ["A Holy Nail of the Crucifixion", "Body of St. Charles Borromeo (in the crypt)"],
     "saints": ["St. Charles Borromeo", "St. Ambrose (patron of Milan)"], "miracles": [],
     "source_url": "https://www.duomomilano.it/en/"},
    {"slug": "seville-cathedral", "name": "Seville Cathedral", "type": "cathedral",
     "city": "Seville", "country": "Spain", "lat": 37.3859, "lng": -5.9932, "founded": "1401–1528",
     "blurb": "The largest Gothic cathedral in the world, with the tomb of Christopher Columbus.",
     "history": "Built on the site of a former mosque (its Giralda was the minaret), it is a UNESCO site and "
     "holds the monumental tomb of Christopher Columbus.",
     "relics": [], "saints": ["St. Ferdinand III of Castile (buried in the royal chapel)"], "miracles": [],
     "source_url": "https://www.catedraldesevilla.es/en/"},
    {"slug": "chartres", "name": "Chartres Cathedral", "type": "cathedral",
     "city": "Chartres", "country": "France", "lat": 48.4474, "lng": 1.4877, "founded": "1194–1220",
     "blurb": "A summit of Gothic art, keeper of the Sancta Camisa, the veil of the Virgin Mary.",
     "history": "Famed for its stained glass and labyrinth, Chartres has been a Marian pilgrimage since the "
     "relic of the Virgin's veil was given by Charles the Bald in 876.",
     "relics": ["The Sancta Camisa (veil of the Blessed Virgin Mary)"], "saints": [], "miracles": [],
     "source_url": "https://www.cathedrale-chartres.org/en/"},
    {"slug": "aachen-cathedral", "name": "Aachen Cathedral", "type": "cathedral",
     "city": "Aachen", "country": "Germany", "lat": 50.7747, "lng": 6.0838, "founded": "796–805",
     "blurb": "Charlemagne's chapel and a great medieval pilgrimage of relics.",
     "history": "The first UNESCO World Heritage Site in Germany, it holds Charlemagne's throne and shrine "
     "and, every seven years, displays its famous Marian relics to pilgrims.",
     "relics": ["The four great Aachen relics (incl. cloak of Mary)", "Shrine of Charlemagne"],
     "saints": [], "miracles": [], "source_url": "https://www.aachenerdom.de/en/"},
    {"slug": "st-stephens-vienna", "name": "St. Stephen's Cathedral", "type": "cathedral",
     "city": "Vienna", "country": "Austria", "lat": 48.2086, "lng": 16.3731, "founded": "1137–1511",
     "blurb": "The soaring Gothic heart of Vienna and of Austrian Catholicism.",
     "history": "With its multicoloured tiled roof and great south tower, 'Steffl' has witnessed Austria's "
     "history for centuries and holds the catacombs of Viennese archbishops.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://www.stephanskirche.at/index.php/en/"},
    {"slug": "holy-blood-bruges", "name": "Basilica of the Holy Blood", "type": "basilica",
     "city": "Bruges", "country": "Belgium", "lat": 51.2086, "lng": 3.2578, "founded": "12th century",
     "blurb": "Home of a venerated relic of the Precious Blood of Christ.",
     "history": "The basilica enshrines a relic of the Holy Blood, said to have been brought from the Holy "
     "Land; it is carried through Bruges each year in the Procession of the Holy Blood.",
     "relics": ["A relic of the Precious Blood of Christ"], "saints": [],
     "miracles": ["The relic of the Holy Blood, venerated for centuries"],
     "source_url": "https://www.holyblood.com/"},
    {"slug": "manila-cathedral", "name": "Manila Cathedral", "type": "cathedral",
     "city": "Manila", "country": "Philippines", "lat": 14.5917, "lng": 120.9742, "founded": "1958 (8th rebuild)",
     "blurb": "The Minor Basilica of the Immaculate Conception, mother church of the Philippines.",
     "history": "Destroyed and rebuilt eight times by fire, earthquake and war, the cathedral stands in "
     "Intramuros as a sign of the resilient faith of the Filipino people.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://manilacathedral.com.ph/"},
    {"slug": "brasilia-cathedral", "name": "Cathedral of Brasília", "type": "cathedral",
     "city": "Brasília", "country": "Brazil", "lat": -15.7986, "lng": -47.8756, "founded": "1958–1970",
     "blurb": "Oscar Niemeyer's luminous modernist cathedral, crowned with soaring white ribs.",
     "history": "Designed by Oscar Niemeyer, its hyperboloid structure of 16 concrete columns opens to the "
     "sky, with suspended angels and a flood of light — a modern hymn in stone and glass.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Cathedral_of_Bras%C3%ADlia"},
    {"slug": "st-josephs-hanoi", "name": "St. Joseph's Cathedral, Hanoi", "type": "cathedral",
     "city": "Hanoi", "country": "Vietnam", "lat": 21.0288, "lng": 105.8490, "founded": "1886",
     "blurb": "The neo-Gothic mother church of Hanoi, dedicated to St. Joseph, patron of Vietnam.",
     "history": "One of the oldest churches in Vietnam, modelled on Notre-Dame de Paris, it remains a "
     "vibrant centre of faith for the Vietnamese Church.",
     "relics": [], "saints": ["St. Joseph (patron of Vietnam)"], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/St._Joseph%27s_Cathedral,_Hanoi"},
    {"slug": "velankanni", "name": "Basilica of Our Lady of Good Health", "type": "basilica",
     "city": "Velankanni", "country": "India", "lat": 10.6800, "lng": 79.8500, "founded": "16th–20th century",
     "blurb": "The 'Lourdes of the East', a great Marian shrine of southern India.",
     "history": "Tradition tells of Our Lady's apparitions to local boys and the rescue of Portuguese "
     "sailors from a storm; the shrine draws millions of pilgrims of every faith for its reported healings.",
     "relics": ["The image of Our Lady of Good Health"], "saints": [],
     "miracles": ["Marian apparitions at Velankanni", "Reported healings"],
     "source_url": "https://en.wikipedia.org/wiki/Basilica_of_Our_Lady_of_Good_Health"},
    {"slug": "sacred-heart-guangzhou", "name": "Sacred Heart Cathedral, Guangzhou", "type": "cathedral",
     "city": "Guangzhou", "country": "China", "lat": 23.1130, "lng": 113.2530, "founded": "1863–1888",
     "blurb": "The 'Stone House' — a rare all-granite Gothic cathedral in southern China.",
     "history": "Built entirely of granite by French missionaries, it is one of the largest Gothic churches "
     "in East Asia and a treasured home for Guangzhou's Catholics.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Sacred_Heart_Cathedral_(Guangzhou)"},
    # ---- Even more of the global Catholic atlas ---- #
    {"slug": "divine-mercy-krakow", "name": "Sanctuary of Divine Mercy, Kraków", "type": "shrine",
     "city": "Kraków", "country": "Poland", "lat": 50.0226, "lng": 19.9447, "founded": "1891 / 2002",
     "blurb": "The world centre of Divine Mercy, holding the tomb of St. Faustina.",
     "history": "Here St. Faustina Kowalska received the revelations of Divine Mercy; the convent and the "
     "great modern basilica consecrated by St. John Paul II draw pilgrims seeking God's mercy.",
     "relics": ["Tomb of St. Faustina Kowalska", "The original Divine Mercy image (nearby)"],
     "saints": ["St. Faustina Kowalska"], "miracles": [],
     "source_url": "https://www.faustyna.pl/zmbm/en/"},
    {"slug": "wawel-cathedral", "name": "Wawel Cathedral", "type": "cathedral",
     "city": "Kraków", "country": "Poland", "lat": 50.0541, "lng": 19.9355, "founded": "1320–1364",
     "blurb": "Poland's coronation cathedral, guarding the relics of St. Stanislaus.",
     "history": "For centuries the coronation and burial church of Polish kings, it enshrines the relics of "
     "St. Stanislaus, bishop and martyr, and was where Karol Wojtyła (St. John Paul II) was ordained bishop.",
     "relics": ["Relics of St. Stanislaus"], "saints": ["St. Stanislaus of Szczepanów"], "miracles": [],
     "source_url": "https://katedra-wawelska.pl/en/"},
    {"slug": "porziuncola", "name": "Basilica of St. Mary of the Angels (Porziuncola)", "type": "basilica",
     "city": "Assisi", "country": "Italy", "lat": 43.0583, "lng": 12.5760, "founded": "1569–1679",
     "blurb": "The great basilica enclosing the tiny Porziuncola chapel beloved of St. Francis.",
     "history": "St. Francis restored this little chapel with his own hands and made it the heart of his "
     "order; here he received the 'Pardon of Assisi' indulgence and died nearby in 1226.",
     "relics": ["The Porziuncola chapel", "The Transito (cell where St. Francis died)"],
     "saints": ["St. Francis of Assisi"], "miracles": ["The Pardon of Assisi indulgence"],
     "source_url": "https://www.porziuncola.org/"},
    {"slug": "st-clare-assisi", "name": "Basilica of St. Clare", "type": "basilica",
     "city": "Assisi", "country": "Italy", "lat": 43.0697, "lng": 12.6190, "founded": "1257–1265",
     "blurb": "Resting place of St. Clare, with the original San Damiano crucifix.",
     "history": "Holding the incorrupt body of St. Clare, foundress of the Poor Clares, the basilica also "
     "preserves the crucifix of San Damiano that spoke to St. Francis: 'Rebuild my Church.'",
     "relics": ["Incorrupt body of St. Clare", "The crucifix of San Damiano"],
     "saints": ["St. Clare of Assisi"], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Basilica_of_Saint_Clare"},
    {"slug": "st-dominic-bologna", "name": "Basilica of San Domenico", "type": "basilica",
     "city": "Bologna", "country": "Italy", "lat": 44.4847, "lng": 11.3470, "founded": "1228–1240",
     "blurb": "Tomb of St. Dominic, founder of the Order of Preachers.",
     "history": "St. Dominic, founder of the Dominicans, is buried in the magnificent 'Arca di San Domenico', "
     "carved by Nicola Pisano and the young Michelangelo among others.",
     "relics": ["Tomb of St. Dominic"], "saints": ["St. Dominic de Guzmán"], "miracles": [],
     "source_url": "https://www.basilicasandomenico.it/"},
    {"slug": "minerva-rome", "name": "Basilica of Santa Maria sopra Minerva", "type": "basilica",
     "city": "Rome", "country": "Italy", "lat": 41.8983, "lng": 12.4779, "founded": "1280–1370",
     "blurb": "Rome's only Gothic church, holding the body of St. Catherine of Siena.",
     "history": "Built over a temple of Minerva, it enshrines the body of St. Catherine of Siena beneath the "
     "high altar and the tomb of the painter Bl. Fra Angelico.",
     "relics": ["Body of St. Catherine of Siena", "Tomb of Bl. Fra Angelico"],
     "saints": ["St. Catherine of Siena", "Bl. Fra Angelico"], "miracles": [],
     "source_url": "https://en.wikipedia.org/wiki/Santa_Maria_sopra_Minerva"},
    {"slug": "san-marco-venice", "name": "St. Mark's Basilica", "type": "basilica",
     "city": "Venice", "country": "Italy", "lat": 45.4345, "lng": 12.3397, "founded": "1063–1094",
     "blurb": "The golden Byzantine basilica of Venice, holding the relics of St. Mark.",
     "history": "Built to enshrine the relics of St. Mark the Evangelist, brought from Alexandria in 828, "
     "the basilica glitters with golden mosaics and the Pala d'Oro altarpiece.",
     "relics": ["Relics of St. Mark the Evangelist"], "saints": ["St. Mark the Evangelist"], "miracles": [],
     "source_url": "https://www.basilicasanmarco.it/?lang=en"},
    {"slug": "orvieto-cathedral", "name": "Orvieto Cathedral", "type": "cathedral",
     "city": "Orvieto", "country": "Italy", "lat": 42.7170, "lng": 12.1135, "founded": "1290–1591",
     "blurb": "Built to enshrine the blood-stained Corporal of the Eucharistic Miracle of Bolsena.",
     "history": "In 1263 a doubting priest at nearby Bolsena saw the Host bleed onto the corporal during "
     "Mass; the relic enshrined here helped inspire the feast of Corpus Christi.",
     "relics": ["The Corporal of the Eucharistic Miracle of Bolsena"], "saints": [],
     "miracles": ["The Eucharistic Miracle of Bolsena (1263)"],
     "source_url": "https://www.opsm.it/en/"},
    {"slug": "st-nicholas-bari", "name": "Basilica of St. Nicholas", "type": "basilica",
     "city": "Bari", "country": "Italy", "lat": 41.1306, "lng": 16.8700, "founded": "1087–1197",
     "blurb": "Resting place of St. Nicholas of Myra, the original 'Santa Claus'.",
     "history": "The relics of St. Nicholas were brought to Bari in 1087; the tomb still exudes a clear "
     "liquid called the 'manna of St. Nicholas', and the basilica is a centre of East-West unity.",
     "relics": ["Relics of St. Nicholas of Myra"], "saints": ["St. Nicholas of Myra"],
     "miracles": ["The 'manna' of St. Nicholas"],
     "source_url": "https://www.basilicasannicola.it/"},
    {"slug": "turin-cathedral", "name": "Turin Cathedral", "type": "cathedral",
     "city": "Turin", "country": "Italy", "lat": 45.0732, "lng": 7.6852, "founded": "1491–1498",
     "blurb": "Home of the Holy Shroud of Turin, believed by many to be Christ's burial cloth.",
     "history": "The cathedral safeguards the Shroud of Turin, a linen bearing the image of a crucified "
     "man, venerated for centuries and the subject of intense scientific study.",
     "relics": ["The Holy Shroud of Turin"], "saints": ["St. John Bosco (Turin)"],
     "miracles": ["The unexplained image on the Shroud of Turin"],
     "source_url": "https://www.sindone.org/en/"},
    {"slug": "naples-cathedral", "name": "Naples Cathedral (San Gennaro)", "type": "cathedral",
     "city": "Naples", "country": "Italy", "lat": 40.8525, "lng": 14.2599, "founded": "1294–1314",
     "blurb": "Where the blood of St. Januarius liquefies several times each year.",
     "history": "The cathedral enshrines vials of the dried blood of St. Januarius, which liquefies on his "
     "feast and other days — a recurring marvel watched by the people of Naples for centuries.",
     "relics": ["The blood and skull of St. Januarius"], "saints": ["St. Januarius (San Gennaro)"],
     "miracles": ["The recurring liquefaction of the blood of St. Januarius"],
     "source_url": "https://en.wikipedia.org/wiki/Naples_Cathedral"},
    {"slug": "manoppello", "name": "Sanctuary of the Holy Face", "type": "shrine",
     "city": "Manoppello", "country": "Italy", "lat": 42.2570, "lng": 14.0590, "founded": "16th century",
     "blurb": "Home of the Holy Face veil, an image of Christ on translucent cloth.",
     "history": "This delicate veil bearing the face of a man — visible from both sides — is venerated as a "
     "relic of Christ's Passion; Pope Benedict XVI visited in 2006.",
     "relics": ["The Holy Face veil of Manoppello"], "saints": [], "miracles": ["The Holy Face image"],
     "source_url": "https://en.wikipedia.org/wiki/Veil_of_Manoppello"},
    {"slug": "lisieux-basilica", "name": "Basilica of St. Thérèse of Lisieux", "type": "basilica",
     "city": "Lisieux", "country": "France", "lat": 49.1380, "lng": 0.2210, "founded": "1929–1954",
     "blurb": "A great basilica honouring St. Thérèse, the 'Little Flower' and Doctor of the Church.",
     "history": "One of the largest churches built in the 20th century, it honours St. Thérèse of Lisieux, "
     "whose 'Little Way' of trust and love has touched millions.",
     "relics": ["Relics of St. Thérèse of Lisieux", "Relics of Sts. Louis & Zélie Martin (Les Buissonnets)"],
     "saints": ["St. Thérèse of Lisieux"], "miracles": [],
     "source_url": "https://www.therese-de-lisieux.catholique.fr/en/"},
    {"slug": "paray-le-monial", "name": "Sanctuary of Paray-le-Monial", "type": "shrine",
     "city": "Paray-le-Monial", "country": "France", "lat": 46.4530, "lng": 4.1150, "founded": "apparitions 1673–75",
     "blurb": "Where the Sacred Heart appeared to St. Margaret Mary Alacoque.",
     "history": "In a series of apparitions, Jesus revealed his Sacred Heart to St. Margaret Mary, asking "
     "for devotion, the Holy Hour, and Communion on First Fridays — devotions now spread worldwide.",
     "relics": ["Relics of St. Margaret Mary Alacoque"], "saints": ["St. Margaret Mary Alacoque", "St. Claude de la Colombière"],
     "miracles": ["The apparitions of the Sacred Heart of Jesus"],
     "source_url": "https://www.sanctuaires-paray.com/en/"},
    {"slug": "nevers-bernadette", "name": "Convent of Saint-Gildard (Nevers)", "type": "shrine",
     "city": "Nevers", "country": "France", "lat": 46.9930, "lng": 3.1620, "founded": "19th century",
     "blurb": "Resting place of the incorrupt body of St. Bernadette Soubirous of Lourdes.",
     "history": "St. Bernadette lived her final years and died here; her body, exhumed and found incorrupt, "
     "lies in a glass reliquary venerated by pilgrims.",
     "relics": ["Incorrupt body of St. Bernadette Soubirous"], "saints": ["St. Bernadette Soubirous"],
     "miracles": ["The incorruption of St. Bernadette's body"],
     "source_url": "https://www.sainte-bernadette-nevers.com/en/"},
    {"slug": "reims-cathedral", "name": "Reims Cathedral", "type": "cathedral",
     "city": "Reims", "country": "France", "lat": 49.2538, "lng": 4.0344, "founded": "1211–1275",
     "blurb": "The coronation church of France, near the baptism of Clovis.",
     "history": "A masterpiece of High Gothic, Reims was the site of the baptism of Clovis (c. 496) and the "
     "coronation of nearly all the kings of France, including Charles VII with St. Joan of Arc present.",
     "relics": [], "saints": ["St. Remigius", "St. Joan of Arc (connected)"], "miracles": [],
     "source_url": "https://www.cathedrale-reims.fr/en/"},
    {"slug": "avila-st-teresa", "name": "Convent of St. Teresa", "type": "monastery",
     "city": "Ávila", "country": "Spain", "lat": 40.6530, "lng": -4.7010, "founded": "1636",
     "blurb": "Built over the birthplace of St. Teresa of Ávila, mystic and Doctor of the Church.",
     "history": "Within the walled city of Ávila, the convent marks the birthplace of St. Teresa, reformer "
     "of Carmel; relics including a relic of her finger are venerated here.",
     "relics": ["Relics of St. Teresa of Ávila"], "saints": ["St. Teresa of Ávila", "St. John of the Cross (Carmelite reform)"],
     "miracles": [], "source_url": "https://en.wikipedia.org/wiki/Convent_of_Saint_Teresa"},
    {"slug": "loyola-sanctuary", "name": "Sanctuary of Loyola", "type": "shrine",
     "city": "Azpeitia", "country": "Spain", "lat": 43.1530, "lng": -2.2680, "founded": "1689–1738",
     "blurb": "Built around the birthplace of St. Ignatius of Loyola, founder of the Jesuits.",
     "history": "The great Baroque basilica surrounds the Holy House where St. Ignatius was born and "
     "converted while recovering from a battle wound — the cradle of the Society of Jesus.",
     "relics": ["The Holy House of Loyola"], "saints": ["St. Ignatius of Loyola"], "miracles": [],
     "source_url": "https://www.santuariodeloyola.org/"},
    {"slug": "bom-jesus-braga", "name": "Bom Jesus do Monte", "type": "shrine",
     "city": "Braga", "country": "Portugal", "lat": 41.5547, "lng": -8.3777, "founded": "18th century",
     "blurb": "A hillside shrine famed for its monumental Baroque stairway of the Five Senses.",
     "history": "Pilgrims climb the dramatic zig-zag stairway, adorned with chapels of the Passion and "
     "fountains, ascending to the church of the Good Jesus of the Mount — a UNESCO World Heritage Site.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://bomjesus.pt/en/"},
    {"slug": "trier-cathedral", "name": "Trier Cathedral", "type": "cathedral",
     "city": "Trier", "country": "Germany", "lat": 49.7549, "lng": 6.6438, "founded": "4th century",
     "blurb": "The oldest cathedral in Germany, holding the Holy Robe of Christ.",
     "history": "Founded in the age of Constantine, Trier Cathedral safeguards the Holy Robe — the seamless "
     "tunic of Christ — displayed to pilgrims on rare occasions.",
     "relics": ["The Holy Robe (Seamless Tunic of Christ)"], "saints": ["St. Helena (associated)"], "miracles": [],
     "source_url": "https://www.dominformation.de/"},
    {"slug": "kevelaer", "name": "Shrine of Our Lady of Kevelaer", "type": "shrine",
     "city": "Kevelaer", "country": "Germany", "lat": 51.5830, "lng": 6.2470, "founded": "1642",
     "blurb": "Germany's largest pilgrimage site, to Our Lady, Consoler of the Afflicted.",
     "history": "Centred on a small image of the Consoler of the Afflicted, Kevelaer has drawn pilgrims "
     "since the 17th century seeking Mary's comfort.",
     "relics": ["The image of Our Lady, Consoler of the Afflicted"], "saints": [], "miracles": [],
     "source_url": "https://www.wallfahrt-kevelaer.de/"},
    {"slug": "croagh-patrick", "name": "Croagh Patrick", "type": "shrine",
     "city": "County Mayo", "country": "Ireland", "lat": 53.7600, "lng": -9.6590, "founded": "5th century",
     "blurb": "St. Patrick's holy mountain, climbed by pilgrims, many barefoot, each year.",
     "history": "Tradition holds that St. Patrick fasted and prayed for forty days on this peak; the "
     "pilgrimage, especially on 'Reek Sunday', is one of Ireland's most ancient.",
     "relics": [], "saints": ["St. Patrick"], "miracles": [],
     "source_url": "https://www.croagh-patrick.com/"},
    {"slug": "medjugorje", "name": "St. James Church, Medjugorje", "type": "apparition",
     "city": "Medjugorje", "country": "Bosnia and Herzegovina", "lat": 43.1910, "lng": 17.6780, "founded": "1981 (reported apparitions)",
     "blurb": "A place of prayer and conversion linked to reported Marian apparitions since 1981.",
     "history": "Six young people reported apparitions of the Queen of Peace beginning in 1981; in 2024 the "
     "Vatican granted a 'nihil obstat', approving Medjugorje as a place of prayer and devotion.",
     "relics": [], "saints": [], "miracles": ["Reported apparitions of the Queen of Peace"],
     "source_url": "https://medjugorje.hr/en/"},
    {"slug": "kibeho", "name": "Shrine of Our Lady of Kibeho", "type": "apparition",
     "city": "Kibeho", "country": "Rwanda", "lat": -2.6230, "lng": 29.5640, "founded": "apparitions 1981–89",
     "blurb": "Africa's approved Marian apparition site, 'Our Lady of Sorrows'.",
     "history": "Our Lady appeared to schoolgirls in Kibeho, calling for prayer and penance and giving "
     "visions later seen as foretelling Rwanda's tragedy; the apparitions were approved in 2001.",
     "relics": [], "saints": [], "miracles": ["The approved apparitions of Our Lady of Kibeho"],
     "source_url": "https://en.wikipedia.org/wiki/Our_Lady_of_Kibeho"},
    {"slug": "champion-wisconsin", "name": "National Shrine of Our Lady of Good Help", "type": "apparition",
     "city": "Champion, WI", "country": "United States", "lat": 44.5360, "lng": -87.8980, "founded": "apparition 1859",
     "blurb": "The only Church-approved Marian apparition site in the United States.",
     "history": "In 1859 the Virgin appeared to Adele Brise, asking her to teach the children their faith. "
     "The apparition was approved in 2010; the grounds were famously spared by the 1871 Peshtigo fire.",
     "relics": [], "saints": [], "miracles": ["The approved apparition (1859)", "Sparing of the shrine in the 1871 fire"],
     "source_url": "https://www.championshrine.org/"},
    {"slug": "carmel-mission", "name": "Mission San Carlos Borromeo (Carmel)", "type": "church",
     "city": "Carmel, California", "country": "United States", "lat": 36.5440, "lng": -121.9190, "founded": "1771",
     "blurb": "Burial place of St. Junípero Serra and his Franciscan mission headquarters.",
     "history": "St. Junípero Serra made this beautiful mission his headquarters and is buried beneath its "
     "sanctuary; it remains a place of pilgrimage in California.",
     "relics": ["Tomb of St. Junípero Serra"], "saints": ["St. Junípero Serra"], "miracles": [],
     "source_url": "https://carmelmission.org/"},
    {"slug": "san-juan-lagos", "name": "Basilica of Our Lady of San Juan de los Lagos", "type": "basilica",
     "city": "San Juan de los Lagos", "country": "Mexico", "lat": 21.2470, "lng": -102.3320, "founded": "1769",
     "blurb": "One of Mexico's most-visited shrines, to a small healing image of Our Lady.",
     "history": "A tiny corn-paste image of the Immaculate Conception, linked to the raising of a child in "
     "1623, draws millions of pilgrims a year to San Juan de los Lagos.",
     "relics": ["The image of Our Lady of San Juan de los Lagos"], "saints": [],
     "miracles": ["The reported raising of a child (1623)"],
     "source_url": "https://en.wikipedia.org/wiki/Our_Lady_of_San_Juan_de_los_Lagos"},
    {"slug": "san-thome-chennai", "name": "San Thome Basilica", "type": "basilica",
     "city": "Chennai", "country": "India", "lat": 13.0330, "lng": 80.2780, "founded": "1896 (over ancient tomb)",
     "blurb": "Built over the tomb of St. Thomas the Apostle, who brought the Gospel to India.",
     "history": "One of only a few churches in the world built over the tomb of an Apostle, it honours St. "
     "Thomas, martyred near Chennai around AD 72.",
     "relics": ["Tomb and relics of St. Thomas the Apostle"], "saints": ["St. Thomas the Apostle"], "miracles": [],
     "source_url": "https://www.santhomechurch.com/"},
    {"slug": "santo-nino-cebu", "name": "Basilica of Santo Niño", "type": "basilica",
     "city": "Cebu", "country": "Philippines", "lat": 10.2940, "lng": 123.9020, "founded": "1565",
     "blurb": "The oldest church in the Philippines, home of the Santo Niño image.",
     "history": "Founded on the spot where the image of the Holy Child Jesus — given by Magellan in 1521 — "
     "was found unburned after a fire, it is the cradle of Philippine Christianity.",
     "relics": ["The Santo Niño (Holy Child) image"], "saints": [],
     "miracles": ["The Santo Niño image found unharmed after a fire"],
     "source_url": "https://basilicasantonino.org.ph/"},
    {"slug": "st-patrick-melbourne", "name": "St Patrick's Cathedral, Melbourne", "type": "cathedral",
     "city": "Melbourne", "country": "Australia", "lat": -37.8100, "lng": 144.9760, "founded": "1858–1939",
     "blurb": "One of the largest Gothic Revival cathedrals in the world.",
     "history": "Seat of the Archbishop of Melbourne, the bluestone cathedral is among the finest examples "
     "of ecclesiastical Gothic architecture in the southern hemisphere.",
     "relics": [], "saints": [], "miracles": [],
     "source_url": "https://melbournecatholic.org/st-patricks-cathedral"},
    {"slug": "cap-de-la-madeleine", "name": "Shrine of Our Lady of the Cape", "type": "shrine",
     "city": "Trois-Rivières", "country": "Canada", "lat": 46.3700, "lng": -72.5160, "founded": "1714 / 1964",
     "blurb": "A national Canadian Marian shrine, site of the 'Miracle of the Eyes'.",
     "history": "In 1888, witnesses reported the statue of Our Lady opened its eyes; the shrine of Our Lady "
     "of the Cape is now one of Canada's foremost Marian pilgrimage sites.",
     "relics": ["The statue of Our Lady of the Cape"], "saints": [], "miracles": ["The 'Miracle of the Eyes' (1888)"],
     "source_url": "https://sanctuaire-ndcap.org/en/"},
    {"slug": "aylesford-priory", "name": "Aylesford Priory (The Friars)", "type": "monastery",
     "city": "Aylesford", "country": "United Kingdom", "lat": 51.3030, "lng": 0.4790, "founded": "1242",
     "blurb": "Ancient Carmelite friary linked to St. Simon Stock and the Brown Scapular.",
     "history": "One of the first Carmelite houses in Europe, Aylesford is associated with St. Simon Stock, "
     "to whom tradition says Our Lady gave the Brown Scapular; restored by the Carmelites in 1949.",
     "relics": ["Relics of St. Simon Stock"], "saints": ["St. Simon Stock"], "miracles": [],
     "source_url": "https://www.thefriars.org.uk/"},
    {"slug": "maipu-chile", "name": "Votive Temple of Maipú", "type": "shrine",
     "city": "Santiago", "country": "Chile", "lat": -33.5160, "lng": -70.7570, "founded": "1948–1974",
     "blurb": "National shrine of Chile, to Our Lady of Mount Carmel, patroness of the nation.",
     "history": "Built fulfilling a vow made at the Battle of Maipú for Chile's independence, the temple "
     "honours Our Lady of Mount Carmel, mother and queen of Chile.",
     "relics": ["The image of Our Lady of Mount Carmel"], "saints": [], "miracles": [],
     "source_url": "https://www.templovotivomaipu.cl/"},
    {"slug": "san-nicolas-argentina", "name": "Shrine of Our Lady of the Rosary of San Nicolás", "type": "apparition",
     "city": "San Nicolás", "country": "Argentina", "lat": -33.3360, "lng": -60.2090, "founded": "apparitions 1983",
     "blurb": "Site of approved Marian apparitions and messages beginning in 1983.",
     "history": "Beginning in 1983, Our Lady appeared to Gladys Quiroga de Motta with messages of prayer "
     "and conversion; the apparitions were approved by the local bishop in 2016.",
     "relics": [], "saints": [], "miracles": ["The approved apparitions of San Nicolás"],
     "source_url": "https://en.wikipedia.org/wiki/Our_Lady_of_San_Nicol%C3%A1s"},
    # ===== Batch: 150 more churches across the world ===== #
    # --- United States --- #
    {"slug": "cathedral-basilica-st-louis", "name": "Cathedral Basilica of Saint Louis", "type": "basilica", "city": "St. Louis, MO", "country": "United States", "lat": 38.6438, "lng": -90.2616, "blurb": "Famed for the largest collection of mosaics in the Western Hemisphere.", "history": "Its breathtaking interior is covered with over 41 million glass tesserae, taking eight decades to complete."},
    {"slug": "cathedral-our-lady-angels-la", "name": "Cathedral of Our Lady of the Angels", "type": "cathedral", "city": "Los Angeles, CA", "country": "United States", "lat": 34.0578, "lng": -118.2460, "blurb": "The bold modern mother church of the Archdiocese of Los Angeles.", "history": "Designed by Rafael Moneo and dedicated in 2002, it holds the relics of St. Vibiana and the tapestries of the Communion of Saints."},
    {"slug": "cathedral-madeleine-slc", "name": "Cathedral of the Madeleine", "type": "cathedral", "city": "Salt Lake City, UT", "country": "United States", "lat": 42.7700, "lng": -111.8880, "blurb": "A richly decorated cathedral honouring St. Mary Magdalene.", "history": "Completed in 1909, its vivid interior murals make it one of the most striking churches in the American West."},
    {"slug": "basilica-sacred-heart-notre-dame", "name": "Basilica of the Sacred Heart", "type": "basilica", "city": "Notre Dame, IN", "country": "United States", "lat": 41.7030, "lng": -86.2390, "blurb": "The grand church at the heart of the University of Notre Dame.", "history": "Its Gothic Revival spire and French stained glass crown the campus founded by the Congregation of Holy Cross."},
    {"slug": "cathedral-st-john-savannah", "name": "Cathedral Basilica of St. John the Baptist", "type": "cathedral", "city": "Savannah, GA", "country": "United States", "lat": 32.0746, "lng": -81.0937, "blurb": "The French Gothic 'mother church' of Catholic Georgia.", "history": "Its twin white spires and painted interior make it one of the most beautiful churches in the American South."},
    {"slug": "cathedral-basilica-st-augustine", "name": "Cathedral Basilica of St. Augustine", "type": "cathedral", "city": "St. Augustine, FL", "country": "United States", "lat": 29.8945, "lng": -81.3130, "blurb": "Seat of the oldest Catholic parish in the United States.", "history": "The parish dates to 1565, the founding of the nation's oldest city; the present basilica preserves Spanish colonial heritage."},
    {"slug": "mission-san-xavier-del-bac", "name": "Mission San Xavier del Bac", "type": "church", "city": "Tucson, AZ", "country": "United States", "lat": 32.1070, "lng": -111.0080, "blurb": "The 'White Dove of the Desert', a jewel of Spanish mission architecture.", "history": "Founded by the Jesuit St. Eusebio Kino and completed by Franciscans in 1797, it still serves the Tohono O'odham people."},
    {"slug": "shrine-most-blessed-sacrament-hanceville", "name": "Shrine of the Most Blessed Sacrament", "type": "shrine", "city": "Hanceville, AL", "country": "United States", "lat": 34.0480, "lng": -86.7760, "blurb": "Mother Angelica's shrine of perpetual adoration in rural Alabama.", "history": "Built by the foundress of EWTN, the Romanesque temple draws pilgrims to its monstrance and cloistered nuns."},
    {"slug": "seton-shrine-emmitsburg", "name": "Basilica of the National Shrine of St. Elizabeth Ann Seton", "type": "basilica", "city": "Emmitsburg, MD", "country": "United States", "lat": 39.6970, "lng": -77.3270, "blurb": "Resting place of the first native-born American saint.", "history": "St. Elizabeth Ann Seton founded the first U.S. religious community and Catholic school system here.", "relics": ["Remains of St. Elizabeth Ann Seton"], "saints": ["St. Elizabeth Ann Seton"]},
    {"slug": "holy-hill-wisconsin", "name": "Basilica of the National Shrine of Mary Help of Christians (Holy Hill)", "type": "basilica", "city": "Hubertus, WI", "country": "United States", "lat": 43.2510, "lng": -88.2240, "blurb": "A hilltop Carmelite shrine famed for reported healings.", "history": "Pilgrims have climbed Holy Hill since the 19th century; its lower chapel displays crutches left by the healed."},
    {"slug": "cathedral-st-paul-mn", "name": "Cathedral of Saint Paul", "type": "cathedral", "city": "St. Paul, MN", "country": "United States", "lat": 44.9462, "lng": -93.1090, "blurb": "A monumental domed cathedral overlooking the Minnesota capital.", "history": "Completed in 1915 in the Classical Revival style, it is among the largest churches in the United States."},
    {"slug": "cathedral-holy-cross-boston", "name": "Cathedral of the Holy Cross", "type": "cathedral", "city": "Boston, MA", "country": "United States", "lat": 42.3380, "lng": -71.0720, "blurb": "The Gothic mother church of the Archdiocese of Boston.", "history": "Dedicated in 1875, it is the largest Catholic church in New England."},
    {"slug": "cathedral-saints-peter-paul-philadelphia", "name": "Cathedral Basilica of Saints Peter and Paul", "type": "basilica", "city": "Philadelphia, PA", "country": "United States", "lat": 39.9590, "lng": -75.1710, "blurb": "The Italian Renaissance cathedral of Philadelphia.", "history": "Its great dome and shrine of St. Katharine Drexel make it a centre of faith in the city of brotherly love."},
    {"slug": "st-james-cathedral-seattle", "name": "St. James Cathedral", "type": "cathedral", "city": "Seattle, WA", "country": "United States", "lat": 47.6080, "lng": -122.3220, "blurb": "The twin-towered cathedral of the Archdiocese of Seattle.", "history": "Dedicated in 1907, its light-filled interior was renewed around a central altar in 1994."},
    {"slug": "old-cathedral-st-louis", "name": "Basilica of St. Louis, King of France (Old Cathedral)", "type": "basilica", "city": "St. Louis, MO", "country": "United States", "lat": 38.6250, "lng": -90.1890, "blurb": "The first cathedral west of the Mississippi, by the Gateway Arch.", "history": "Built in 1834, it is the oldest cathedral and the spiritual cradle of Catholicism in the American West."},
    {"slug": "shrine-our-lady-snows-belleville", "name": "National Shrine of Our Lady of the Snows", "type": "shrine", "city": "Belleville, IL", "country": "United States", "lat": 38.5360, "lng": -90.0560, "blurb": "One of the largest outdoor shrines in North America.", "history": "Run by the Missionary Oblates of Mary Immaculate, its vast grounds welcome a million pilgrims a year."},
    {"slug": "cathedral-immaculate-conception-denver", "name": "Cathedral Basilica of the Immaculate Conception", "type": "basilica", "city": "Denver, CO", "country": "United States", "lat": 39.7440, "lng": -104.9800, "blurb": "The Gothic Revival basilica of the Mile-High City.", "history": "Its soaring twin spires and German stained glass have crowned Denver since 1911."},
    {"slug": "co-cathedral-sacred-heart-houston", "name": "Co-Cathedral of the Sacred Heart", "type": "cathedral", "city": "Houston, TX", "country": "United States", "lat": 29.7560, "lng": -95.3680, "blurb": "A grand modern co-cathedral for the largest U.S. archdiocese by area.", "history": "Dedicated in 2008, it serves the Archdiocese of Galveston-Houston."},
    # --- Canada --- #
    {"slug": "notre-dame-basilica-montreal", "name": "Notre-Dame Basilica of Montreal", "type": "basilica", "city": "Montreal", "country": "Canada", "lat": 45.5046, "lng": -73.5560, "blurb": "A Gothic Revival masterpiece glowing with deep blue and gold.", "history": "Its dazzling interior, carved and gilded, is among the most beautiful churches in North America."},
    {"slug": "notre-dame-cathedral-ottawa", "name": "Notre-Dame Cathedral Basilica", "type": "basilica", "city": "Ottawa", "country": "Canada", "lat": 45.4290, "lng": -75.6950, "blurb": "The oldest and largest church in Canada's capital.", "history": "Its twin silver spires have marked the Ottawa skyline since the 1840s."},
    {"slug": "st-michael-cathedral-toronto", "name": "St. Michael's Cathedral Basilica", "type": "basilica", "city": "Toronto", "country": "Canada", "lat": 43.6560, "lng": -79.3760, "blurb": "The mother church of Catholic Toronto.", "history": "Built in 1848 in the English Gothic style, it was beautifully restored in 2016."},
    {"slug": "notre-dame-quebec", "name": "Cathedral-Basilica of Notre-Dame de Québec", "type": "basilica", "city": "Quebec City", "country": "Canada", "lat": 46.8140, "lng": -71.2060, "blurb": "The primatial church of Canada, the oldest north of Mexico.", "history": "Founded in 1647, it holds a Holy Door and the tombs of the bishops of Quebec, including St. François de Laval.", "saints": ["St. François de Laval"]},
    # --- Latin America --- #
    {"slug": "buenos-aires-cathedral", "name": "Buenos Aires Metropolitan Cathedral", "type": "cathedral", "city": "Buenos Aires", "country": "Argentina", "lat": -34.6080, "lng": -58.3720, "blurb": "Where Pope Francis served as archbishop before his election.", "history": "It holds the mausoleum of the liberator General San Martín and a venerated image of Our Lady."},
    {"slug": "sao-paulo-cathedral", "name": "São Paulo Cathedral (Sé)", "type": "cathedral", "city": "São Paulo", "country": "Brazil", "lat": -23.5500, "lng": -46.6340, "blurb": "A vast neo-Gothic cathedral at the heart of Brazil's largest city.", "history": "One of the largest neo-Gothic churches in the world, completed in 1954."},
    {"slug": "nazare-belem", "name": "Basilica of Our Lady of Nazaré", "type": "basilica", "city": "Belém", "country": "Brazil", "lat": -1.4520, "lng": -48.4900, "blurb": "Centre of the Círio de Nazaré, one of the world's largest Marian processions.", "history": "Each October millions accompany the image of Our Lady of Nazareth through Belém."},
    {"slug": "san-salvador-cathedral", "name": "Metropolitan Cathedral of San Salvador", "type": "cathedral", "city": "San Salvador", "country": "El Salvador", "lat": 13.6990, "lng": -89.1910, "blurb": "Resting place of the martyr St. Óscar Romero.", "history": "Archbishop Romero, martyred in 1980 and canonized in 2018, is buried in its crypt; he loved the poor of El Salvador.", "relics": ["Tomb of St. Óscar Romero"], "saints": ["St. Óscar Romero"]},
    {"slug": "leon-cathedral-nicaragua", "name": "León Cathedral", "type": "cathedral", "city": "León", "country": "Nicaragua", "lat": 12.4350, "lng": -86.8780, "blurb": "The largest cathedral in Central America, a UNESCO site.", "history": "Its luminous white interior guards the tomb of the poet Rubén Darío, kept by a weeping stone lion."},
    {"slug": "lima-cathedral", "name": "Lima Cathedral", "type": "cathedral", "city": "Lima", "country": "Peru", "lat": -12.0460, "lng": -77.0300, "blurb": "The Spanish colonial cathedral on Lima's Plaza Mayor.", "history": "Founded by Francisco Pizarro in 1535, whose remains lie in a chapel within."},
    {"slug": "cusco-cathedral", "name": "Cusco Cathedral", "type": "cathedral", "city": "Cusco", "country": "Peru", "lat": -13.5160, "lng": -71.9780, "blurb": "An Andean Baroque cathedral built atop an Inca palace.", "history": "Its art blends Spanish and indigenous traditions, including a famed Last Supper with roast guinea pig."},
    {"slug": "compania-quito", "name": "Church of La Compañía de Jesús", "type": "church", "city": "Quito", "country": "Ecuador", "lat": -0.2200, "lng": -78.5150, "blurb": "A dazzling Jesuit church gilded with seven tonnes of gold.", "history": "The jewel of Quito's Baroque, its interior shimmers entirely in gold leaf."},
    {"slug": "bogota-cathedral", "name": "Primatial Cathedral of Bogotá", "type": "cathedral", "city": "Bogotá", "country": "Colombia", "lat": 4.5980, "lng": -74.0760, "blurb": "The neoclassical cathedral on Bogotá's Plaza Bolívar.", "history": "One of the largest cathedrals in South America, seat of the Colombian primate."},
    {"slug": "cartagena-cathedral", "name": "Cartagena Cathedral", "type": "cathedral", "city": "Cartagena", "country": "Colombia", "lat": 10.4230, "lng": -75.5510, "blurb": "A fortress-like cathedral in the walled Caribbean city.", "history": "Begun in the 16th century, it withstood the cannon of Sir Francis Drake."},
    {"slug": "santiago-cathedral-chile", "name": "Santiago Metropolitan Cathedral", "type": "cathedral", "city": "Santiago", "country": "Chile", "lat": -33.4380, "lng": -70.6510, "blurb": "The neoclassical cathedral on Santiago's Plaza de Armas.", "history": "Seat of the Archbishop of Santiago, rebuilt after earthquakes over four centuries."},
    {"slug": "montevideo-cathedral", "name": "Montevideo Metropolitan Cathedral", "type": "cathedral", "city": "Montevideo", "country": "Uruguay", "lat": -34.9080, "lng": -56.2030, "blurb": "The oldest public building in Montevideo's old town.", "history": "Consecrated in 1804, it holds the remains of several national figures."},
    {"slug": "guadalajara-cathedral", "name": "Guadalajara Cathedral", "type": "cathedral", "city": "Guadalajara", "country": "Mexico", "lat": 20.6770, "lng": -103.3490, "blurb": "Twin yellow-tiled spires define the skyline of Guadalajara.", "history": "Begun in 1561, it blends Gothic, Baroque and Neoclassical styles."},
    {"slug": "puebla-cathedral", "name": "Puebla Cathedral", "type": "cathedral", "city": "Puebla", "country": "Mexico", "lat": 19.0430, "lng": -98.1980, "blurb": "A grand Baroque cathedral with the tallest towers in Mexico.", "history": "Consecrated in 1649, its richly gilded interior is a marvel of New Spain."},
    {"slug": "remedios-cholula", "name": "Sanctuary of Our Lady of Remedies (Cholula)", "type": "shrine", "city": "Cholula", "country": "Mexico", "lat": 19.0580, "lng": -98.3020, "blurb": "A church crowning the world's largest pyramid.", "history": "Built by the Spanish atop the Great Pyramid of Cholula, with views of the volcanoes."},
    {"slug": "panama-cathedral", "name": "Panama City Metropolitan Cathedral", "type": "cathedral", "city": "Panama City", "country": "Panama", "lat": 8.9510, "lng": -79.5340, "blurb": "The historic cathedral of Panama's Casco Viejo.", "history": "Completed in 1796, its towers are inlaid with mother-of-pearl."},
    {"slug": "tegucigalpa-cathedral", "name": "Tegucigalpa Cathedral", "type": "cathedral", "city": "Tegucigalpa", "country": "Honduras", "lat": 14.1010, "lng": -87.2060, "blurb": "The Baroque cathedral of the Honduran capital.", "history": "Dedicated to St. Michael the Archangel, completed in 1782."},
    {"slug": "templo-expiatorio-guadalajara", "name": "Templo Expiatorio del Santísimo Sacramento", "type": "church", "city": "Guadalajara", "country": "Mexico", "lat": 20.6730, "lng": -103.3640, "blurb": "A neo-Gothic temple of perpetual adoration.", "history": "Built over fifty years, its German clock features automated figures of the Apostles."},
    # --- Italy --- #
    {"slug": "florence-duomo", "name": "Florence Cathedral (Santa Maria del Fiore)", "type": "cathedral", "city": "Florence", "country": "Italy", "lat": 43.7730, "lng": 11.2560, "blurb": "Crowned by Brunelleschi's revolutionary dome.", "history": "Its dome, the largest masonry dome ever built, became the symbol of the Renaissance."},
    {"slug": "pisa-cathedral", "name": "Pisa Cathedral", "type": "cathedral", "city": "Pisa", "country": "Italy", "lat": 43.7230, "lng": 10.3960, "blurb": "The medieval cathedral beside the famous Leaning Tower.", "history": "A masterpiece of Pisan Romanesque, begun in 1063 on the Piazza dei Miracoli."},
    {"slug": "siena-cathedral", "name": "Siena Cathedral", "type": "cathedral", "city": "Siena", "country": "Italy", "lat": 43.3170, "lng": 11.3290, "blurb": "A striped Gothic cathedral with an unrivalled inlaid marble floor.", "history": "Its dazzling black-and-white marble and Piccolomini Library make it a treasure of Tuscan art."},
    {"slug": "st-paul-outside-walls", "name": "Basilica of St. Paul Outside the Walls", "type": "basilica", "city": "Rome", "country": "Italy", "lat": 41.8590, "lng": 12.4770, "blurb": "One of Rome's four papal basilicas, over the tomb of St. Paul.", "history": "Built over the burial place of the Apostle Paul, it preserves a chain believed to have bound him.", "relics": ["Tomb of St. Paul the Apostle"], "saints": ["St. Paul the Apostle"]},
    {"slug": "st-cecilia-trastevere", "name": "Basilica of St. Cecilia in Trastevere", "type": "basilica", "city": "Rome", "country": "Italy", "lat": 41.8870, "lng": 12.4760, "blurb": "Built over the home of the patroness of music, St. Cecilia.", "history": "It holds the famous Maderno statue of the incorrupt St. Cecilia as she was found.", "relics": ["Relics of St. Cecilia"], "saints": ["St. Cecilia"]},
    {"slug": "san-clemente-rome", "name": "Basilica of San Clemente", "type": "basilica", "city": "Rome", "country": "Italy", "lat": 41.8890, "lng": 12.4970, "blurb": "A church built in three layers across two thousand years.", "history": "Beneath the medieval basilica lie a 4th-century church and a Roman Mithraic temple.", "saints": ["Pope St. Clement I"]},
    {"slug": "monreale-cathedral", "name": "Monreale Cathedral", "type": "cathedral", "city": "Monreale", "country": "Italy", "lat": 38.0820, "lng": 13.2920, "blurb": "A Norman cathedral covered in shimmering golden mosaics.", "history": "Its 12th-century Byzantine mosaics depicting the whole Bible are among the finest in the world."},
    {"slug": "palermo-cathedral", "name": "Palermo Cathedral", "type": "cathedral", "city": "Palermo", "country": "Italy", "lat": 38.1140, "lng": 13.3560, "blurb": "A cathedral of many styles, holding the relics of St. Rosalia.", "history": "St. Rosalia, patroness of Palermo, is venerated here; her relics are said to have ended a plague.", "relics": ["Relics of St. Rosalia"], "saints": ["St. Rosalia"]},
    {"slug": "amalfi-cathedral", "name": "Amalfi Cathedral", "type": "cathedral", "city": "Amalfi", "country": "Italy", "lat": 40.6340, "lng": 14.6030, "blurb": "A dramatic striped cathedral above the Amalfi Coast, holding St. Andrew's relics.", "history": "The Apostle St. Andrew's relics, brought from Constantinople in 1208, rest in its crypt; a 'manna' forms on them.", "relics": ["Relics of St. Andrew the Apostle"], "saints": ["St. Andrew the Apostle"]},
    {"slug": "la-verna", "name": "Sanctuary of La Verna", "type": "shrine", "city": "Chiusi della Verna", "country": "Italy", "lat": 43.7080, "lng": 11.9330, "blurb": "The mountain where St. Francis received the stigmata.", "history": "On this rugged peak in 1224, St. Francis of Assisi received the wounds of Christ in his own body.", "saints": ["St. Francis of Assisi"], "miracles": ["The stigmata of St. Francis"]},
    {"slug": "cascia-st-rita", "name": "Basilica of St. Rita of Cascia", "type": "basilica", "city": "Cascia", "country": "Italy", "lat": 42.7180, "lng": 13.0130, "blurb": "Home of St. Rita, patroness of impossible causes.", "history": "The incorrupt body of St. Rita, wife, mother and nun, draws those who pray for the impossible.", "relics": ["Incorrupt body of St. Rita"], "saints": ["St. Rita of Cascia"]},
    {"slug": "pompeii-rosary", "name": "Pontifical Shrine of Our Lady of the Rosary of Pompeii", "type": "shrine", "city": "Pompeii", "country": "Italy", "lat": 40.7490, "lng": 14.5010, "blurb": "A great Marian shrine beside the ancient ruins of Pompeii.", "history": "Founded by Bl. Bartolo Longo, it spread the Rosary and works of charity from the shadow of Vesuvius.", "saints": ["Bl. Bartolo Longo"]},
    {"slug": "subiaco-sacro-speco", "name": "Sacro Speco (Sacred Cave of St. Benedict)", "type": "monastery", "city": "Subiaco", "country": "Italy", "lat": 41.9170, "lng": 13.1230, "blurb": "The cave where St. Benedict lived as a hermit.", "history": "Clinging to a cliff, the monastery preserves the cave of St. Benedict and the earliest known portrait of St. Francis.", "saints": ["St. Benedict of Nursia"]},
    {"slug": "genoa-cathedral", "name": "Genoa Cathedral (San Lorenzo)", "type": "cathedral", "city": "Genoa", "country": "Italy", "lat": 44.4070, "lng": 8.9310, "blurb": "A striped Romanesque-Gothic cathedral holding precious relics.", "history": "Its treasury claims the Sacro Catino, a green glass dish associated with the Last Supper."},
    {"slug": "ravenna-san-vitale", "name": "Basilica of San Vitale", "type": "basilica", "city": "Ravenna", "country": "Italy", "lat": 44.4200, "lng": 12.1970, "blurb": "A 6th-century church glittering with Byzantine mosaics.", "history": "Its mosaics of Emperor Justinian and Theodora are the supreme survival of early Christian Byzantine art."},
    # --- France --- #
    {"slug": "strasbourg-cathedral", "name": "Strasbourg Cathedral", "type": "cathedral", "city": "Strasbourg", "country": "France", "lat": 48.5820, "lng": 7.7510, "blurb": "A soaring rose-sandstone Gothic cathedral with a famed astronomical clock.", "history": "Once the tallest building in the world, its single spire and clockwork apostles astonish pilgrims."},
    {"slug": "amiens-cathedral", "name": "Amiens Cathedral", "type": "cathedral", "city": "Amiens", "country": "France", "lat": 49.8950, "lng": 2.3020, "blurb": "The largest Gothic cathedral in France, keeping a relic of St. John the Baptist.", "history": "It enshrines a relic venerated as the face of the head of St. John the Baptist, brought from the Crusades.", "relics": ["Relic of St. John the Baptist"], "saints": ["St. John the Baptist"]},
    {"slug": "vezelay", "name": "Basilica of St. Mary Magdalene, Vézelay", "type": "basilica", "city": "Vézelay", "country": "France", "lat": 47.4660, "lng": 3.7480, "blurb": "A Romanesque pilgrimage basilica with relics of St. Mary Magdalene.", "history": "A starting point of the Camino, it draws pilgrims to the relics of St. Mary Magdalene.", "relics": ["Relics of St. Mary Magdalene"], "saints": ["St. Mary Magdalene"]},
    {"slug": "conques-sainte-foy", "name": "Abbey of Sainte-Foy, Conques", "type": "monastery", "city": "Conques", "country": "France", "lat": 44.6010, "lng": 2.4000, "blurb": "A Romanesque pilgrim abbey holding the golden reliquary of St. Faith.", "history": "Its jewel-encrusted reliquary statue of the child-martyr St. Faith is a marvel of medieval art.", "relics": ["Relics of St. Faith (Sainte Foy)"], "saints": ["St. Faith"]},
    {"slug": "fourviere-lyon", "name": "Basilica of Notre-Dame de Fourvière", "type": "basilica", "city": "Lyon", "country": "France", "lat": 45.7620, "lng": 4.8220, "blurb": "A white basilica crowning the hill above Lyon.", "history": "Built in thanksgiving after the city was spared in war, it is dedicated to the Virgin who protects Lyon."},
    {"slug": "notre-dame-garde-marseille", "name": "Basilica of Notre-Dame de la Garde", "type": "basilica", "city": "Marseille", "country": "France", "lat": 43.2840, "lng": 5.3710, "blurb": "'La Bonne Mère' watching over Marseille from her hilltop.", "history": "Crowned by a golden statue of the Madonna, she is the beloved protectress of sailors and the city."},
    {"slug": "tours-st-martin", "name": "Basilica of St. Martin, Tours", "type": "basilica", "city": "Tours", "country": "France", "lat": 47.3930, "lng": 0.6840, "blurb": "Over the tomb of St. Martin, one of the great early pilgrimages of Europe.", "history": "St. Martin of Tours, who shared his cloak with a beggar, is buried here; his shrine drew medieval pilgrims from afar.", "relics": ["Tomb of St. Martin of Tours"], "saints": ["St. Martin of Tours"]},
    {"slug": "le-puy-cathedral", "name": "Le Puy-en-Velay Cathedral", "type": "cathedral", "city": "Le Puy-en-Velay", "country": "France", "lat": 45.0440, "lng": 3.8840, "blurb": "A dramatic pilgrimage cathedral and starting point of the Camino.", "history": "Home of a Black Madonna and one of the four great French starting points of the road to Santiago."},
    {"slug": "rocamadour", "name": "Sanctuary of Rocamadour", "type": "shrine", "city": "Rocamadour", "country": "France", "lat": 44.7990, "lng": 1.6180, "blurb": "A cliffside shrine of the Black Madonna reached by a pilgrim stairway.", "history": "Pilgrims climb the Grand Escalier on their knees to the chapel of the venerated Black Virgin."},
    {"slug": "saint-denis-basilica", "name": "Basilica of Saint-Denis", "type": "basilica", "city": "Saint-Denis", "country": "France", "lat": 48.9350, "lng": 2.3590, "blurb": "The birthplace of Gothic architecture and necropolis of French kings.", "history": "Built over the tomb of St. Denis, it pioneered the Gothic style and holds the tombs of nearly all France's monarchs.", "saints": ["St. Denis of Paris"]},
    {"slug": "albi-cathedral", "name": "Albi Cathedral (Sainte-Cécile)", "type": "cathedral", "city": "Albi", "country": "France", "lat": 43.9280, "lng": 2.1430, "blurb": "The largest brick cathedral in the world, a fortress of faith.", "history": "Its austere brick exterior hides a vividly painted Gothic interior and a vast Last Judgement fresco."},
    # --- Spain & Portugal --- #
    {"slug": "burgos-cathedral", "name": "Burgos Cathedral", "type": "cathedral", "city": "Burgos", "country": "Spain", "lat": 42.3410, "lng": -3.7040, "blurb": "A UNESCO Gothic masterpiece on the Camino de Santiago.", "history": "Begun in 1221, it holds the tomb of the national hero El Cid and breathtaking openwork spires."},
    {"slug": "leon-cathedral-spain", "name": "León Cathedral", "type": "cathedral", "city": "León", "country": "Spain", "lat": 42.5990, "lng": -5.5670, "blurb": "Famed for the most luminous stained glass in Spain.", "history": "Its nearly 1,800 square metres of medieval glass earned it the name 'House of Light'."},
    {"slug": "granada-cathedral", "name": "Granada Cathedral", "type": "cathedral", "city": "Granada", "country": "Spain", "lat": 37.1760, "lng": -3.5990, "blurb": "A Renaissance cathedral beside the royal chapel of the Catholic Monarchs.", "history": "Built after the reconquest of Granada in 1492, its adjoining chapel holds Ferdinand and Isabella."},
    {"slug": "cordoba-mezquita-catedral", "name": "Mosque–Cathedral of Córdoba", "type": "cathedral", "city": "Córdoba", "country": "Spain", "lat": 37.8790, "lng": -4.7790, "blurb": "A Christian cathedral within a forest of Moorish arches.", "history": "A UNESCO World Heritage Site, its cathedral nave rises amid the famous striped arches of the former mosque."},
    {"slug": "valencia-cathedral", "name": "Valencia Cathedral", "type": "cathedral", "city": "Valencia", "country": "Spain", "lat": 39.4760, "lng": -0.3750, "blurb": "Home of a chalice venerated as the Holy Grail.", "history": "Its Holy Chalice, used by popes at Mass, is honoured by many as the cup of the Last Supper.", "relics": ["The Holy Chalice (Santo Cáliz)"]},
    {"slug": "oviedo-cathedral", "name": "Oviedo Cathedral", "type": "cathedral", "city": "Oviedo", "country": "Spain", "lat": 43.3620, "lng": -5.8430, "blurb": "Keeper of the Sudarium, a cloth said to have covered Christ's face.", "history": "Its Cámara Santa preserves the Sudarium of Oviedo and other relics saved from the Muslim conquest.", "relics": ["The Sudarium of Oviedo"]},
    {"slug": "salamanca-cathedral", "name": "Salamanca Cathedrals (New & Old)", "type": "cathedral", "city": "Salamanca", "country": "Spain", "lat": 40.9600, "lng": -5.6680, "blurb": "Twin cathedrals, late Gothic joined to Romanesque.", "history": "The golden-stoned New Cathedral adjoins the 12th-century Old Cathedral with its frescoed dome."},
    {"slug": "lisbon-cathedral", "name": "Lisbon Cathedral (Sé)", "type": "cathedral", "city": "Lisbon", "country": "Portugal", "lat": 38.7100, "lng": -9.1330, "blurb": "The oldest church in Lisbon, fortress-like and Romanesque.", "history": "Begun in 1147 after the city's reconquest, it has survived earthquakes for nearly 900 years."},
    {"slug": "porto-cathedral", "name": "Porto Cathedral (Sé do Porto)", "type": "cathedral", "city": "Porto", "country": "Portugal", "lat": 41.1430, "lng": -8.6110, "blurb": "A fortified Romanesque cathedral above the Douro.", "history": "One of Portugal's oldest monuments, where Prince Henry the Navigator was baptized."},
    # --- Germany, Austria, Switzerland & Central Europe --- #
    {"slug": "munich-frauenkirche", "name": "Munich Frauenkirche", "type": "cathedral", "city": "Munich", "country": "Germany", "lat": 48.1390, "lng": 11.5730, "blurb": "Munich's landmark cathedral with twin onion-domed towers.", "history": "Home of the famous 'Devil's Footprint' legend and the tomb of Emperor Louis IV."},
    {"slug": "bamberg-cathedral", "name": "Bamberg Cathedral", "type": "cathedral", "city": "Bamberg", "country": "Germany", "lat": 49.8910, "lng": 10.8820, "blurb": "An imperial cathedral holding the only papal tomb in Germany.", "history": "It contains the tombs of Pope Clement II and of Sts. Henry II and Cunigunde, and the enigmatic Bamberg Horseman.", "relics": ["Tombs of Sts. Henry II and Cunigunde"], "saints": ["St. Henry II", "St. Cunigunde"]},
    {"slug": "speyer-cathedral", "name": "Speyer Cathedral", "type": "cathedral", "city": "Speyer", "country": "Germany", "lat": 49.3170, "lng": 8.4420, "blurb": "The largest Romanesque church in the world.", "history": "A UNESCO World Heritage Site and burial place of eight Holy Roman Emperors and kings."},
    {"slug": "mainz-cathedral", "name": "Mainz Cathedral", "type": "cathedral", "city": "Mainz", "country": "Germany", "lat": 50.0000, "lng": 8.2740, "blurb": "A thousand-year-old imperial cathedral of red sandstone.", "history": "Seat of the influential archbishops of Mainz, it has stood at the heart of German church history since 975."},
    {"slug": "regensburg-cathedral", "name": "Regensburg Cathedral", "type": "cathedral", "city": "Regensburg", "country": "Germany", "lat": 49.0190, "lng": 12.0980, "blurb": "Bavaria's finest Gothic cathedral, home of a famous boys' choir.", "history": "Its Domspatzen ('cathedral sparrows') choir dates back over a thousand years."},
    {"slug": "freiburg-minster", "name": "Freiburg Minster", "type": "cathedral", "city": "Freiburg", "country": "Germany", "lat": 47.9950, "lng": 7.8520, "blurb": "Famed for a tower called 'the most beautiful spire in Christendom'.", "history": "Its openwork Gothic spire survived the bombing of 1944 that flattened the surrounding city."},
    {"slug": "salzburg-cathedral", "name": "Salzburg Cathedral", "type": "cathedral", "city": "Salzburg", "country": "Austria", "lat": 47.7980, "lng": 13.0470, "blurb": "A Baroque cathedral where Mozart was baptized.", "history": "Its font, where Mozart became a Christian, and rich domes make it the heart of Salzburg."},
    {"slug": "vienna-st-stephens", "name": "St. Stephen's Cathedral, Vienna", "type": "cathedral", "city": "Vienna", "country": "Austria", "lat": 48.2086, "lng": 16.3731, "blurb": "Vienna's Gothic icon with its multicoloured tiled roof.", "history": "'Steffl' has presided over Austria's history for centuries and holds the imperial catacombs."},
    {"slug": "warsaw-st-john-cathedral", "name": "St. John's Archcathedral", "type": "cathedral", "city": "Warsaw", "country": "Poland", "lat": 52.2490, "lng": 21.0140, "blurb": "The mother church of Warsaw, rebuilt after wartime destruction.", "history": "Razed in 1944, it was faithfully reconstructed; Polish kings were crowned and primates are buried here."},
    {"slug": "gniezno-cathedral", "name": "Gniezno Cathedral", "type": "cathedral", "city": "Gniezno", "country": "Poland", "lat": 52.5380, "lng": 17.5930, "blurb": "The cradle of the Polish Church, holding St. Adalbert's relics.", "history": "First capital of Poland, its bronze Gniezno Doors depict the life of the martyr St. Adalbert.", "relics": ["Relics of St. Adalbert"], "saints": ["St. Adalbert of Prague"]},
    {"slug": "krakow-st-marys", "name": "St. Mary's Basilica, Kraków", "type": "basilica", "city": "Kraków", "country": "Poland", "lat": 50.0617, "lng": 19.9390, "blurb": "Famed for its hourly trumpet call and Veit Stoss altarpiece.", "history": "Its towering Gothic altarpiece by Veit Stoss is the largest in the world; a bugle sounds every hour from its tower."},
    {"slug": "budapest-st-stephens", "name": "St. Stephen's Basilica", "type": "basilica", "city": "Budapest", "country": "Hungary", "lat": 47.5010, "lng": 19.0540, "blurb": "Budapest's great basilica, holding the Holy Right hand of St. Stephen.", "history": "Its most precious relic is the mummified right hand of St. Stephen, first king of Hungary, paraded each August.", "relics": ["The Holy Right (hand of St. Stephen)"], "saints": ["St. Stephen of Hungary"]},
    {"slug": "zagreb-cathedral", "name": "Zagreb Cathedral", "type": "cathedral", "city": "Zagreb", "country": "Croatia", "lat": 45.8140, "lng": 15.9790, "blurb": "The tallest building in Croatia, with twin Gothic spires.", "history": "Dedicated to the Assumption, it holds the tomb of Bl. Alojzije Stepinac.", "saints": ["Bl. Alojzije Stepinac"]},
    {"slug": "ljubljana-cathedral", "name": "Ljubljana Cathedral", "type": "cathedral", "city": "Ljubljana", "country": "Slovenia", "lat": 46.0510, "lng": 14.5080, "blurb": "A green-domed Baroque cathedral with magnificent bronze doors.", "history": "Its modern bronze doors, carved for John Paul II's visit, depict the history of Slovenian Christianity."},
    {"slug": "vilnius-cathedral", "name": "Vilnius Cathedral", "type": "cathedral", "city": "Vilnius", "country": "Lithuania", "lat": 54.6860, "lng": 25.2880, "blurb": "The neoclassical heart of Lithuanian Catholicism.", "history": "It holds the Chapel of St. Casimir, patron of Lithuania, and the royal mausoleum.", "saints": ["St. Casimir"]},
    {"slug": "bratislava-st-martin", "name": "St. Martin's Cathedral, Bratislava", "type": "cathedral", "city": "Bratislava", "country": "Slovakia", "lat": 48.1420, "lng": 17.1050, "blurb": "The Gothic coronation church of the kings of Hungary.", "history": "Eleven monarchs were crowned here; a gilded crown tops its spire in memory."},
    {"slug": "brussels-cathedral", "name": "Cathedral of St. Michael and St. Gudula", "type": "cathedral", "city": "Brussels", "country": "Belgium", "lat": 50.8480, "lng": 4.3600, "blurb": "The national cathedral of Belgium, a Brabantine Gothic gem.", "history": "Site of royal weddings and state funerals, with stained glass given by Habsburg rulers."},
    {"slug": "antwerp-cathedral", "name": "Cathedral of Our Lady, Antwerp", "type": "cathedral", "city": "Antwerp", "country": "Belgium", "lat": 51.2200, "lng": 4.4030, "blurb": "The largest Gothic church in the Low Countries, hung with Rubens.", "history": "It treasures masterpieces by Peter Paul Rubens, including 'The Raising of the Cross'."},
    {"slug": "ghent-st-bavo", "name": "St. Bavo's Cathedral, Ghent", "type": "cathedral", "city": "Ghent", "country": "Belgium", "lat": 51.0530, "lng": 3.7270, "blurb": "Home of the Ghent Altarpiece by the Van Eyck brothers.", "history": "Its 'Adoration of the Mystic Lamb' (1432) is among the most important paintings in Western art."},
    {"slug": "den-bosch-st-john", "name": "St. John's Cathedral, 's-Hertogenbosch", "type": "cathedral", "city": "'s-Hertogenbosch", "country": "Netherlands", "lat": 51.6880, "lng": 5.3060, "blurb": "The finest Gothic church in the Netherlands.", "history": "Famed for its hundreds of carved figures and a miraculous image of Our Lady (the Zoete Lieve Vrouw)."},
    {"slug": "luxembourg-notre-dame", "name": "Notre-Dame Cathedral, Luxembourg", "type": "cathedral", "city": "Luxembourg City", "country": "Luxembourg", "lat": 49.6100, "lng": 6.1310, "blurb": "The only cathedral in the Grand Duchy, honouring the national patroness.", "history": "It enshrines the venerated image of Our Lady, Comforter of the Afflicted, patroness of Luxembourg."},
    {"slug": "copenhagen-cathedral", "name": "Cathedral of St. Ansgar, Copenhagen", "type": "cathedral", "city": "Copenhagen", "country": "Denmark", "lat": 55.6850, "lng": 12.5790, "blurb": "The Catholic cathedral of Denmark, named for the 'Apostle of the North'.", "history": "Dedicated to St. Ansgar, the 9th-century missionary who first brought the Gospel to Scandinavia."},
    {"slug": "stockholm-st-eric", "name": "Cathedral of St. Eric, Stockholm", "type": "cathedral", "city": "Stockholm", "country": "Sweden", "lat": 59.3140, "lng": 18.0660, "blurb": "The Catholic cathedral of Sweden, honouring the nation's patron.", "history": "Named for St. Eric, king and martyr, it serves Sweden's growing Catholic community."},
    {"slug": "helsinki-st-henry", "name": "St. Henry's Cathedral, Helsinki", "type": "cathedral", "city": "Helsinki", "country": "Finland", "lat": 60.1640, "lng": 24.9540, "blurb": "Finland's oldest Catholic church, named for its patron saint.", "history": "Dedicated to St. Henry, the medieval bishop and martyr who evangelized Finland.", "saints": ["St. Henry of Finland"]},
    {"slug": "tallinn-cathedral", "name": "Cathedral of Sts. Peter and Paul, Tallinn", "type": "cathedral", "city": "Tallinn", "country": "Estonia", "lat": 59.4370, "lng": 24.7440, "blurb": "The only Catholic cathedral in Estonia.", "history": "A neo-Gothic church serving Catholics in the Estonian capital since 1845."},
    {"slug": "lucerne-hofkirche", "name": "Hofkirche St. Leodegar", "type": "church", "city": "Lucerne", "country": "Switzerland", "lat": 47.0560, "lng": 8.3110, "blurb": "Lucerne's twin-spired church, a fine Renaissance survival.", "history": "Famed for one of the most important organs in Switzerland."},
    {"slug": "bucharest-st-joseph", "name": "St. Joseph Cathedral, Bucharest", "type": "cathedral", "city": "Bucharest", "country": "Romania", "lat": 44.4380, "lng": 26.0940, "blurb": "The Roman Catholic cathedral of Romania's capital.", "history": "A neo-Romanesque church serving the Latin-rite Catholics of Bucharest since 1884."},
    # --- Asia & Middle East --- #
    {"slug": "mount-mary-bandra", "name": "Basilica of Our Lady of the Mount", "type": "basilica", "city": "Mumbai", "country": "India", "lat": 19.0440, "lng": 72.8190, "blurb": "Mumbai's hilltop Marian basilica, drawing the annual Bandra Fair.", "history": "Its centuries-old image of Our Lady of the Mount attracts pilgrims of every faith."},
    {"slug": "st-mary-basilica-bangalore", "name": "St. Mary's Basilica, Bangalore", "type": "basilica", "city": "Bengaluru", "country": "India", "lat": 12.9870, "lng": 77.5790, "blurb": "One of the oldest churches in Bangalore and a Marian pilgrimage centre.", "history": "Famed for its September feast of Mary, when thousands gather for the festival of the Nativity of Our Lady."},
    {"slug": "sacred-heart-pondicherry", "name": "Basilica of the Sacred Heart of Jesus", "type": "basilica", "city": "Puducherry", "country": "India", "lat": 11.9270, "lng": 79.8260, "blurb": "A Gothic basilica built by French missionaries in colonial Pondicherry.", "history": "Its rare stained glass depicts the life of Christ and saints of the Church."},
    {"slug": "se-cathedral-goa", "name": "Sé Cathedral, Old Goa", "type": "cathedral", "city": "Old Goa", "country": "India", "lat": 15.5040, "lng": 73.9120, "blurb": "One of the largest churches in Asia, with the 'Golden Bell'.", "history": "Built to mark the Portuguese victory, its great bell is among the best-sounding in the world."},
    {"slug": "san-agustin-manila", "name": "San Agustín Church, Manila", "type": "church", "city": "Manila", "country": "Philippines", "lat": 14.5890, "lng": 120.9750, "blurb": "The oldest stone church in the Philippines, a UNESCO site.", "history": "Completed in 1607, it survived earthquakes and wars that destroyed every church around it."},
    {"slug": "saigon-notre-dame", "name": "Saigon Notre-Dame Basilica", "type": "basilica", "city": "Ho Chi Minh City", "country": "Vietnam", "lat": 10.7800, "lng": 106.6990, "blurb": "A red-brick French colonial basilica with twin bell towers.", "history": "Built entirely of materials imported from France, it is a beloved landmark of Saigon."},
    {"slug": "jeoldusan-shrine", "name": "Jeoldu-san Martyrs' Shrine", "type": "shrine", "city": "Seoul", "country": "South Korea", "lat": 37.5470, "lng": 126.9320, "blurb": "A shrine where many Korean Catholics were martyred.", "history": "On 'Beheading Hill' above the Han River, thousands gave their lives for the faith in the 19th century.", "saints": ["The Korean Martyrs"]},
    {"slug": "urakami-cathedral", "name": "Urakami Cathedral", "type": "cathedral", "city": "Nagasaki", "country": "Japan", "lat": 32.7770, "lng": 129.8680, "blurb": "Rebuilt over the epicentre district of the atomic bomb.", "history": "Once the largest church in East Asia, it was destroyed by the 1945 bomb and rebuilt; relics survive as a witness to peace."},
    {"slug": "macau-st-paul-ruins", "name": "Ruins of St. Paul's", "type": "church", "city": "Macau", "country": "China", "lat": 22.1980, "lng": 113.5410, "blurb": "The majestic stone façade of a 17th-century Jesuit church.", "history": "Once 'the greatest church in the East', only its carved façade survived an 1835 fire — Macau's enduring symbol."},
    {"slug": "beijing-north-church", "name": "Church of the Saviour (Xishiku)", "type": "church", "city": "Beijing", "country": "China", "lat": 39.9230, "lng": 116.3760, "blurb": "Beijing's historic 'North Church', a Gothic survivor.", "history": "Famed for the 1900 siege when Catholics sheltered within during the Boxer Rebellion."},
    {"slug": "hongkong-immaculate-conception", "name": "Cathedral of the Immaculate Conception", "type": "cathedral", "city": "Hong Kong", "country": "China", "lat": 22.2780, "lng": 114.1540, "blurb": "The Gothic Revival cathedral of Hong Kong.", "history": "Consecrated in 1888, it has served the faith through colonial and modern times."},
    {"slug": "colombo-st-lucia", "name": "St. Lucia's Cathedral, Colombo", "type": "cathedral", "city": "Colombo", "country": "Sri Lanka", "lat": 6.9450, "lng": 79.8650, "blurb": "The largest church in Sri Lanka, seat of the Colombo archdiocese.", "history": "Its great neoclassical dome has presided over Sri Lankan Catholicism since the 19th century."},
    {"slug": "yangon-st-mary", "name": "St. Mary's Cathedral, Yangon", "type": "cathedral", "city": "Yangon", "country": "Myanmar", "lat": 16.7820, "lng": 96.1620, "blurb": "The largest cathedral in Myanmar, in red brick Gothic.", "history": "Completed in 1911, it is the seat of the Archbishop of Yangon."},
    {"slug": "singapore-good-shepherd", "name": "Cathedral of the Good Shepherd", "type": "cathedral", "city": "Singapore", "country": "Singapore", "lat": 1.2950, "lng": 103.8500, "blurb": "The oldest Catholic church in Singapore.", "history": "Built in 1847 in the Renaissance style, it is the mother church of Singapore's Catholics."},
    {"slug": "kl-st-john", "name": "Cathedral of St. John, Kuala Lumpur", "type": "cathedral", "city": "Kuala Lumpur", "country": "Malaysia", "lat": 3.1500, "lng": 101.7000, "blurb": "The Catholic cathedral of the Malaysian capital.", "history": "Serving since 1883, it is the seat of the Archdiocese of Kuala Lumpur."},
    {"slug": "gethsemane-agony", "name": "Church of All Nations (Basilica of the Agony)", "type": "basilica", "city": "Jerusalem", "country": "Israel/Palestine", "lat": 31.7790, "lng": 35.2400, "blurb": "Built over the rock where Jesus prayed in Gethsemane.", "history": "It enshrines the stone where, by tradition, Christ prayed in agony the night before he died.", "relics": ["The Rock of the Agony"]},
    {"slug": "nativity-bethlehem", "name": "Church of the Nativity", "type": "basilica", "city": "Bethlehem", "country": "Israel/Palestine", "lat": 31.7042, "lng": 35.2076, "blurb": "Built over the cave where Jesus Christ was born.", "history": "One of the oldest churches in continuous use, its silver star marks the traditional birthplace of Christ.", "relics": ["The Grotto of the Nativity"]},
    {"slug": "annunciation-nazareth", "name": "Basilica of the Annunciation", "type": "basilica", "city": "Nazareth", "country": "Israel/Palestine", "lat": 32.7020, "lng": 35.2980, "blurb": "Built over the home where the angel Gabriel greeted Mary.", "history": "The largest church in the Middle East, it enshrines the grotto of the Annunciation."},
    {"slug": "dormition-jerusalem", "name": "Dormition Abbey", "type": "monastery", "city": "Jerusalem", "country": "Israel/Palestine", "lat": 31.7710, "lng": 35.2290, "blurb": "Marks the place of the 'falling asleep' of the Virgin Mary.", "history": "A German Benedictine abbey on Mount Zion honouring the Dormition of Our Lady."},
    {"slug": "istanbul-st-anthony", "name": "Church of St. Anthony of Padua, Istanbul", "type": "church", "city": "Istanbul", "country": "Turkey", "lat": 41.0330, "lng": 28.9770, "blurb": "The largest Catholic church in Istanbul, on İstiklal Avenue.", "history": "A red-brick Venetian Neo-Gothic church where Pope John XXIII once preached as apostolic delegate."},
    # --- Africa --- #
    {"slug": "notre-dame-afrique-algiers", "name": "Notre-Dame d'Afrique", "type": "basilica", "city": "Algiers", "country": "Algeria", "lat": 36.8000, "lng": 3.0420, "blurb": "A basilica overlooking the bay, beloved by Christians and Muslims.", "history": "Its apse inscription prays for both Christians and Muslims, a sign of friendship in North Africa."},
    {"slug": "carthage-acropolium", "name": "Acropolium (St. Louis Cathedral, Carthage)", "type": "cathedral", "city": "Carthage", "country": "Tunisia", "lat": 36.8580, "lng": 10.3230, "blurb": "A cathedral on the hill of ancient Carthage, land of St. Augustine.", "history": "Built where St. Louis of France died in 1270, near the city of St. Cyprian and St. Augustine."},
    {"slug": "casablanca-cathedral", "name": "Casablanca Cathedral (Sacré-Cœur)", "type": "cathedral", "city": "Casablanca", "country": "Morocco", "lat": 33.5890, "lng": -7.6190, "blurb": "A striking white Art Deco former cathedral.", "history": "Its bold modernist towers blend European and Moroccan design."},
    {"slug": "dakar-cathedral", "name": "Cathedral of Our Lady of Victories", "type": "cathedral", "city": "Dakar", "country": "Senegal", "lat": 14.6630, "lng": -17.4290, "blurb": "The 'African Memorial' cathedral of Senegal.", "history": "Built to honour African Catholics, blending Sudanese and Byzantine styles."},
    {"slug": "accra-holy-spirit", "name": "Holy Spirit Cathedral, Accra", "type": "cathedral", "city": "Accra", "country": "Ghana", "lat": 5.5470, "lng": -0.2010, "blurb": "The mother church of Catholic Ghana.", "history": "Seat of the Archdiocese of Accra, serving a flourishing West African Church."},
    {"slug": "lagos-holy-cross", "name": "Holy Cross Cathedral, Lagos", "type": "cathedral", "city": "Lagos", "country": "Nigeria", "lat": 6.4490, "lng": 3.3920, "blurb": "The historic cathedral of Lagos.", "history": "Seat of the Archdiocese of Lagos, central to Nigeria's vibrant Catholic life."},
    {"slug": "rubaga-cathedral", "name": "Rubaga Cathedral", "type": "cathedral", "city": "Kampala", "country": "Uganda", "lat": 0.3060, "lng": 32.5560, "blurb": "The mother church of Uganda, on Rubaga Hill.", "history": "It holds the relics of St. Joseph Mukasa, one of the Uganda Martyrs.", "saints": ["St. Joseph Mukasa Balikuddembe"]},
    {"slug": "harare-sacred-heart", "name": "Cathedral of the Sacred Heart, Harare", "type": "cathedral", "city": "Harare", "country": "Zimbabwe", "lat": -17.8290, "lng": 31.0490, "blurb": "The Catholic cathedral of Zimbabwe's capital.", "history": "Seat of the Archdiocese of Harare, serving the Church in southern Africa."},
    {"slug": "andohalo-cathedral", "name": "Andohalo Cathedral", "type": "cathedral", "city": "Antananarivo", "country": "Madagascar", "lat": -18.9170, "lng": 47.5300, "blurb": "A stone cathedral overlooking the Malagasy capital.", "history": "Built on the site where Malagasy Christians were martyred, it is a symbol of the island's faith."},
    {"slug": "cape-town-st-mary", "name": "St. Mary's Cathedral, Cape Town", "type": "cathedral", "city": "Cape Town", "country": "South Africa", "lat": -33.9270, "lng": 18.4170, "blurb": "The oldest Catholic cathedral in South Africa.", "history": "Mother church of the Archdiocese of Cape Town, serving since 1851."},
    # --- Oceania --- #
    {"slug": "st-stephen-brisbane", "name": "St. Stephen's Cathedral, Brisbane", "type": "cathedral", "city": "Brisbane", "country": "Australia", "lat": -27.4660, "lng": 153.0290, "blurb": "The Gothic Revival cathedral of Brisbane.", "history": "Designed in part by A.W.N. Pugin, it is the seat of the Archbishop of Brisbane."},
    {"slug": "st-francis-xavier-adelaide", "name": "St Francis Xavier's Cathedral, Adelaide", "type": "cathedral", "city": "Adelaide", "country": "Australia", "lat": -34.9270, "lng": 138.5990, "blurb": "The mother church of Catholic South Australia.", "history": "Begun in 1856, it is dedicated to the great missionary St. Francis Xavier."},
    {"slug": "st-mary-perth", "name": "St Mary's Cathedral, Perth", "type": "cathedral", "city": "Perth", "country": "Australia", "lat": -31.9520, "lng": 115.8650, "blurb": "The cathedral of the Archdiocese of Perth, beautifully renewed.", "history": "Its 2009 restoration married the original Gothic church with a luminous modern nave."},
    {"slug": "sacred-heart-wellington", "name": "Sacred Heart Cathedral, Wellington", "type": "cathedral", "city": "Wellington", "country": "New Zealand", "lat": -41.2920, "lng": 174.7790, "blurb": "The metropolitan cathedral of New Zealand's capital.", "history": "A classical basilica-style church, seat of the Cardinal Archbishop of Wellington."},
    {"slug": "apia-cathedral", "name": "Cathedral of the Immaculate Conception, Apia", "type": "cathedral", "city": "Apia", "country": "Samoa", "lat": -13.8330, "lng": -171.7600, "blurb": "A gleaming white cathedral on Samoa's waterfront.", "history": "Rebuilt and reconsecrated in 2014, it is the heart of the Catholic Church in the Pacific nation."},
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
        "persecuted": bool(doc.get("persecuted", False)),
        "persecution_note": doc.get("persecution_note", ""),
        "osm": bool(doc.get("osm", False)),
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
    str_fields = ["name", "blurb", "history", "city", "country", "founded", "persecution_note"]
    list_fields = ["relics", "saints", "miracles"]
    for i, it in enumerate(items):
        if it.get("osm"):
            continue  # community-sourced churches are not translated (volume)
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

    @router.get("/nearby")
    async def nearby_sites(lat: float | None = None, lng: float | None = None, user=Depends(get_current_user)):
        await _seed_if_missing(db)
        items = [_public(d) async for d in col.find({}, {"_id": 0})]
        if lat is not None and lng is not None:
            import math
            def dist(s):
                dlat = math.radians((s.get("lat") or 0) - lat)
                dlng = math.radians((s.get("lng") or 0) - lng)
                a = (math.sin(dlat / 2) ** 2 +
                     math.cos(math.radians(lat)) * math.cos(math.radians(s.get("lat") or 0)) * math.sin(dlng / 2) ** 2)
                return 6371 * 2 * math.asin(min(1, math.sqrt(a)))
            for s in items:
                s["distance_km"] = round(dist(s), 1)
            items.sort(key=lambda s: s.get("distance_km", 1e9))
        else:
            # No location: offer a stable "saint of the place" pick that rotates daily.
            from datetime import date as _d
            items.sort(key=lambda s: s.get("name") or "")
            if items:
                items = items[(_d.today().toordinal() % len(items)):] + items[:(_d.today().toordinal() % len(items))]
        top = items[:8]
        await _localize(db, top)
        return {"items": top, "total": len(top)}

    @router.get("/{site_id}")
    async def get_site(site_id: str, user=Depends(get_current_user)):
        doc = await col.find_one({"$or": [{"site_id": site_id}, {"slug": site_id}]}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Site not found")
        item = _public(doc)
        await _localize(db, [item])
        return item

    return router
