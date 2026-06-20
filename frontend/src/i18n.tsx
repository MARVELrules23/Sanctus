/**
 * Lightweight i18n for Sanctus (English / Spanish).
 *
 * Wrap the app in <LanguageProvider>. Use `const { t, lang, setLang } = useI18n()`
 * and replace user-facing strings with `t("key")`. Missing Spanish keys fall
 * back to English, so screens can be migrated to t() incrementally.
 *
 * The chosen language is persisted in AsyncStorage and also exposed via
 * `getLang()` so non-React code (e.g. API helpers) can read it.
 */
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

export type Lang = "en" | "es" | "it";
const STORAGE_KEY = "sanctus_lang";

let _currentLang: Lang = "en";
/** Read the active language outside React (e.g. to send to the API). */
export function getLang(): Lang {
  return _currentLang;
}

type Dict = Record<string, string>;

const en: Dict = {
  // common
  "common.today": "Today",
  "common.save": "Save",
  "common.saveChanges": "Save changes",
  "common.add": "Add",
  "common.edit": "Edit",
  "common.delete": "Delete",
  "common.cancel": "Cancel",
  "common.tryAgain": "Try again",
  "common.allDay": "All day",
  "common.loading": "Loading…",
  "common.openSettings": "Open Settings",
  "common.notNow": "Not now",
  "common.somethingWrong": "Something went wrong.",
  // tabs
  "tab.today": "Today",
  "tab.meals": "Meals",
  "tab.workouts": "Workouts",
  "tab.wellness": "Wellness",
  "tab.calendar": "Calendar",
  "tab.parish": "Parish",
  "tab.sanctuary": "Sanctuary",
  "tab.profile": "Profile",
  // home quick tiles
  "home.prayer": "Prayer",
  "home.journal": "Journal",
  "home.grocery": "Grocery",
  "home.bible": "Bible",
  "home.calendar": "Calendar",
  "home.churches": "Churches",
  "home.examen": "Examen",
  "home.selfDefense": "Self-Defense",
  "home.charities": "Charities",
  "home.schedule": "Schedule",
  "home.scheduleSub": "Your rhythm of prayer & practice",
  "home.world": "In the World",
  "home.worldSub": "Public life through Catholic teaching",
  "home.quickActions": "Quick actions",
  "home.language": "Language",
  // virtus home card
  "virtus.home.tagline": "Grow in holiness — study a virtue and set a goal to live it well.",
  "virtus.home.explore": "Explore the virtues",
  // virtus hub
  "virtus.subtitle": "Grow in holiness, one virtue at a time",
  "virtus.heroTitle": "The school of virtue",
  "virtus.heroSub": "Study the virtues, learn to live them in every season of life, and set a goal to grow in the ones the Lord is calling you toward.",
  "virtus.workOn": "Work on a virtue",
  "virtus.chooseHint": "Choose one or more virtues to focus on.",
  "virtus.timeframe": "Over what timeframe?",
  "virtus.days": "{n} days",
  "virtus.notePlaceholder": "Anything you'd like the plan to address? (optional)",
  "virtus.pickToBegin": "Pick a virtue to begin",
  "virtus.buildPlan": "Build my {n}-day plan",
  "virtus.yourPlans": "YOUR PLANS",
  "virtus.theVirtues": "THE VIRTUES",
  "virtus.goalsEnds": "{done}/{total} goals · ends {date}",
  // schedule
  "schedule.title": "Schedule",
  "schedule.subtitle": "Plan your week with the Church",
  "schedule.every": "EVERY {day}",
  "schedule.nothing": "Nothing scheduled on this day yet.",
  "schedule.upcoming": "UPCOMING ONE-OFF",
  "schedule.addToSchedule": "Add to schedule",
  "schedule.remindersNote": "Reminders fire on the built iOS/Android app — not in this web preview.",
  // schedule editor
  "schedule.addTitle": "Add to schedule",
  "schedule.editTitle": "Edit item",
  "schedule.type": "TYPE",
  "schedule.kind.meal": "Meal",
  "schedule.kind.workout": "Workout",
  "schedule.kind.virtue": "Virtue",
  "schedule.kind.challenge": "Challenge",
  "schedule.kind.custom": "Custom",
  "schedule.titleLabel": "TITLE",
  "schedule.repeats": "REPEATS",
  "schedule.weekly": "Weekly",
  "schedule.oneDate": "One date",
  "schedule.time": "TIME",
  "schedule.hour": "Hour",
  "schedule.minute": "Minute",
  "schedule.remindMe": "Remind me",
  "schedule.remindOn": "A notification at the scheduled time.",
  "schedule.remindBuild": "Reminders fire on the built app, not in preview.",
  "schedule.noteOptional": "NOTE (OPTIONAL)",
  "schedule.notePlaceholder": "Anything to remember…",
  "schedule.activePlan": "ACTIVE VIRTUE PLAN",
  "schedule.enrolledChallenge": "ENROLLED CHALLENGE",
  "schedule.noPlans": "No active virtue plans — start one in Virtus.",
  "schedule.noChallenges": "You're not enrolled in any challenges yet.",
  "schedule.addToCalendar": "ADD TO YOUR CALENDAR",
  "schedule.calendarHint": "Put this on Google or your phone's calendar so it sends the reminders.",
  "schedule.googleCal": "Google Calendar",
  "schedule.appleCal": "Apple / phone calendar",
  "schedule.openFull": "Open full schedule",
  "schedule.nothingDay": "Nothing scheduled for this day.",
  // settings / profile
  "settings.language": "Language",
  "settings.languageHint": "Choose the language for the app and AI content.",
  "profile.title": "Profile",
  "profile.defaultName": "Faithful soul",
  "profile.myEvents": "My Events",
  "profile.journal": "Journal",
  "profile.nourishment": "Nourishment",
  "profile.dietary": "Dietary pattern",
  "profile.allergies": "Allergies / things to avoid",
  "profile.allergiesPh": "e.g. nuts, shellfish",
  "profile.discipline": "Discipline",
  "profile.fitnessLevel": "Fitness level",
  "profile.goal": "Goal",
  "profile.goalPh": "e.g. build endurance, lose weight",
  "profile.devotion": "Devotion",
  "profile.focus": "Focus",
  "profile.focusPh": "e.g. daily Mass, rosary, Liturgy of the Hours",
  "profile.saved": "Saved",
  "profile.about": "About",
  "profile.premium": "Sanctus Premium",
  "profile.premiumManage": "Sanctus Premium · Manage",
  "profile.shop": "Sanctus Shop",
  "profile.orders": "My Orders",
  "profile.support": "Help & Support",
  "profile.privacy": "Privacy Policy",
  "profile.signOut": "Sign out",
  "profile.footer": "Ad maiorem Dei gloriam — for the greater glory of God.",
  // schedule editor extras
  "schedule.deleteTitle": "Delete this item?",
  "schedule.deleteMsg": "It will be removed from your schedule.",
  "schedule.remindOffTitle": "Reminders are off",
  "schedule.remindOffMsg": "Enable notifications for Sanctus in Settings to get schedule reminders.",
  "schedule.needTitle": "Add a title",
  "schedule.needTitleMsg": "Give this item a name.",
  "schedule.pickDay": "Pick a day",
  "schedule.pickDayMsg": "Choose at least one day of the week.",
  "schedule.cantSave": "Couldn't save",
  "schedule.tryAgain": "Please try again.",
  "schedule.phMeal": "e.g. Breakfast",
  "schedule.phWorkout": "e.g. Leg day",
  "schedule.phWhat": "What is it?",
  // virtue detail
  "virtus.detail.whatIs": "What it is",
  "virtus.detail.whyMatters": "Why it matters",
  "virtus.detail.living": "Living it in every season",
  "virtus.detail.saints": "Saints who lived it",
  "virtus.detail.prayer": "A prayer",
  "virtus.detail.resources": "Resources to go deeper",
  "virtus.detail.startPlan": "Start a plan for this virtue",
  "virtus.detail.premiumLocked": "Premium resources",
  "virtus.detail.unlock": "Unlock with Sanctus Premium",
};

const es: Dict = {
  // common
  "common.today": "Hoy",
  "common.save": "Guardar",
  "common.saveChanges": "Guardar cambios",
  "common.add": "Añadir",
  "common.edit": "Editar",
  "common.delete": "Eliminar",
  "common.cancel": "Cancelar",
  "common.tryAgain": "Intentar de nuevo",
  "common.allDay": "Todo el día",
  "common.loading": "Cargando…",
  "common.openSettings": "Abrir Ajustes",
  "common.notNow": "Ahora no",
  "common.somethingWrong": "Algo salió mal.",
  // tabs
  "tab.today": "Hoy",
  "tab.meals": "Comidas",
  "tab.workouts": "Ejercicios",
  "tab.wellness": "Bienestar",
  "tab.calendar": "Calendario",
  "tab.parish": "Parroquia",
  "tab.sanctuary": "Santuario",
  "tab.profile": "Perfil",
  // home quick tiles
  "home.prayer": "Oración",
  "home.journal": "Diario",
  "home.grocery": "Compras",
  "home.bible": "Biblia",
  "home.calendar": "Calendario",
  "home.churches": "Iglesias",
  "home.examen": "Examen",
  "home.selfDefense": "Defensa Personal",
  "home.charities": "Caridades",
  "home.schedule": "Horario",
  "home.scheduleSub": "Tu ritmo de oración y práctica",
  "home.world": "En el Mundo",
  "home.worldSub": "La vida pública a la luz de la Iglesia",
  "home.quickActions": "Acciones rápidas",
  "home.language": "Idioma",
  // virtus home card
  "virtus.home.tagline": "Crece en santidad: estudia una virtud y proponte una meta para vivirla bien.",
  "virtus.home.explore": "Explorar las virtudes",
  // virtus hub
  "virtus.subtitle": "Crece en santidad, una virtud a la vez",
  "virtus.heroTitle": "La escuela de la virtud",
  "virtus.heroSub": "Estudia las virtudes, aprende a vivirlas en cada etapa de la vida y proponte crecer en aquellas a las que el Señor te llama.",
  "virtus.workOn": "Trabaja una virtud",
  "virtus.chooseHint": "Elige una o más virtudes en las que enfocarte.",
  "virtus.timeframe": "¿En qué plazo?",
  "virtus.days": "{n} días",
  "virtus.notePlaceholder": "¿Algo que quieras que el plan trate? (opcional)",
  "virtus.pickToBegin": "Elige una virtud para empezar",
  "virtus.buildPlan": "Crear mi plan de {n} días",
  "virtus.yourPlans": "TUS PLANES",
  "virtus.theVirtues": "LAS VIRTUDES",
  "virtus.goalsEnds": "{done}/{total} metas · termina {date}",
  // schedule
  "schedule.title": "Horario",
  "schedule.subtitle": "Planifica tu semana con la Iglesia",
  "schedule.every": "CADA {day}",
  "schedule.nothing": "Aún no hay nada programado para este día.",
  "schedule.upcoming": "PRÓXIMO (UNA VEZ)",
  "schedule.addToSchedule": "Añadir al horario",
  "schedule.remindersNote": "Los recordatorios suenan en la app compilada de iOS/Android, no en esta vista web.",
  // schedule editor
  "schedule.addTitle": "Añadir al horario",
  "schedule.editTitle": "Editar elemento",
  "schedule.type": "TIPO",
  "schedule.kind.meal": "Comida",
  "schedule.kind.workout": "Ejercicio",
  "schedule.kind.virtue": "Virtud",
  "schedule.kind.challenge": "Desafío",
  "schedule.kind.custom": "Personal",
  "schedule.titleLabel": "TÍTULO",
  "schedule.repeats": "SE REPITE",
  "schedule.weekly": "Semanal",
  "schedule.oneDate": "Una fecha",
  "schedule.time": "HORA",
  "schedule.hour": "Hora",
  "schedule.minute": "Minuto",
  "schedule.remindMe": "Recuérdamelo",
  "schedule.remindOn": "Una notificación a la hora programada.",
  "schedule.remindBuild": "Los recordatorios suenan en la app compilada, no en la vista previa.",
  "schedule.noteOptional": "NOTA (OPCIONAL)",
  "schedule.notePlaceholder": "Algo que recordar…",
  "schedule.activePlan": "PLAN DE VIRTUD ACTIVO",
  "schedule.enrolledChallenge": "DESAFÍO INSCRITO",
  "schedule.noPlans": "No hay planes de virtud activos: empieza uno en Virtus.",
  "schedule.noChallenges": "Aún no estás inscrito en ningún desafío.",
  "schedule.addToCalendar": "AÑADIR A TU CALENDARIO",
  "schedule.calendarHint": "Añádelo a Google o al calendario de tu teléfono para que él envíe los recordatorios.",
  "schedule.googleCal": "Google Calendar",
  "schedule.appleCal": "Calendario de Apple / teléfono",
  "schedule.openFull": "Abrir horario completo",
  "schedule.nothingDay": "Nada programado para este día.",
  // settings / profile
  "settings.language": "Idioma",
  "settings.languageHint": "Elige el idioma de la app y del contenido con IA.",
  "profile.title": "Perfil",
  "profile.defaultName": "Alma fiel",
  "profile.myEvents": "Mis eventos",
  "profile.journal": "Diario",
  "profile.nourishment": "Alimentación",
  "profile.dietary": "Patrón alimenticio",
  "profile.allergies": "Alergias / cosas a evitar",
  "profile.allergiesPh": "p. ej. nueces, mariscos",
  "profile.discipline": "Disciplina",
  "profile.fitnessLevel": "Nivel físico",
  "profile.goal": "Meta",
  "profile.goalPh": "p. ej. ganar resistencia, bajar de peso",
  "profile.devotion": "Devoción",
  "profile.focus": "Enfoque",
  "profile.focusPh": "p. ej. Misa diaria, rosario, Liturgia de las Horas",
  "profile.saved": "Guardado",
  "profile.about": "Acerca de",
  "profile.premium": "Sanctus Premium",
  "profile.premiumManage": "Sanctus Premium · Gestionar",
  "profile.shop": "Tienda Sanctus",
  "profile.orders": "Mis pedidos",
  "profile.support": "Ayuda y soporte",
  "profile.privacy": "Política de privacidad",
  "profile.signOut": "Cerrar sesión",
  "profile.footer": "Ad maiorem Dei gloriam — para la mayor gloria de Dios.",
  // schedule editor extras
  "schedule.deleteTitle": "¿Eliminar este elemento?",
  "schedule.deleteMsg": "Se eliminará de tu horario.",
  "schedule.remindOffTitle": "Los recordatorios están desactivados",
  "schedule.remindOffMsg": "Activa las notificaciones de Sanctus en Ajustes para recibir recordatorios.",
  "schedule.needTitle": "Añade un título",
  "schedule.needTitleMsg": "Dale un nombre a este elemento.",
  "schedule.pickDay": "Elige un día",
  "schedule.pickDayMsg": "Elige al menos un día de la semana.",
  "schedule.cantSave": "No se pudo guardar",
  "schedule.tryAgain": "Inténtalo de nuevo.",
  "schedule.phMeal": "p. ej. Desayuno",
  "schedule.phWorkout": "p. ej. Día de piernas",
  "schedule.phWhat": "¿Qué es?",
  // virtue detail
  "virtus.detail.whatIs": "Qué es",
  "virtus.detail.whyMatters": "Por qué importa",
  "virtus.detail.living": "Vivirla en cada etapa",
  "virtus.detail.saints": "Santos que la vivieron",
  "virtus.detail.prayer": "Una oración",
  "virtus.detail.resources": "Recursos para profundizar",
  "virtus.detail.startPlan": "Crear un plan para esta virtud",
  "virtus.detail.premiumLocked": "Recursos premium",
  "virtus.detail.unlock": "Desbloquea con Sanctus Premium",
};

const it: Dict = {
  // common
  "common.today": "Oggi",
  "common.save": "Salva",
  "common.saveChanges": "Salva modifiche",
  "common.add": "Aggiungi",
  "common.edit": "Modifica",
  "common.delete": "Elimina",
  "common.cancel": "Annulla",
  "common.tryAgain": "Riprova",
  "common.allDay": "Tutto il giorno",
  "common.loading": "Caricamento…",
  "common.openSettings": "Apri Impostazioni",
  "common.notNow": "Non ora",
  "common.somethingWrong": "Qualcosa è andato storto.",
  // tabs
  "tab.today": "Oggi",
  "tab.meals": "Pasti",
  "tab.workouts": "Allenamenti",
  "tab.wellness": "Benessere",
  "tab.calendar": "Calendario",
  "tab.parish": "Parrocchia",
  "tab.sanctuary": "Santuario",
  "tab.profile": "Profilo",
  // home quick tiles
  "home.prayer": "Preghiera",
  "home.journal": "Diario",
  "home.grocery": "Spesa",
  "home.bible": "Bibbia",
  "home.calendar": "Calendario",
  "home.churches": "Chiese",
  "home.examen": "Esame",
  "home.selfDefense": "Autodifesa",
  "home.charities": "Opere di carità",
  "home.schedule": "Orario",
  "home.scheduleSub": "Il tuo ritmo di preghiera e pratica",
  "home.world": "Nel Mondo",
  "home.worldSub": "La vita pubblica alla luce della Chiesa",
  "home.quickActions": "Azioni rapide",
  "home.language": "Lingua",
  // virtus home card
  "virtus.home.tagline": "Cresci nella santità — studia una virtù e poniti un obiettivo per viverla bene.",
  "virtus.home.explore": "Esplora le virtù",
  // virtus hub
  "virtus.subtitle": "Cresci nella santità, una virtù alla volta",
  "virtus.heroTitle": "La scuola della virtù",
  "virtus.heroSub": "Studia le virtù, impara a viverle in ogni stagione della vita e poniti un obiettivo per crescere in quelle a cui il Signore ti chiama.",
  "virtus.workOn": "Lavora su una virtù",
  "virtus.chooseHint": "Scegli una o più virtù su cui concentrarti.",
  "virtus.timeframe": "In quale arco di tempo?",
  "virtus.days": "{n} giorni",
  "virtus.notePlaceholder": "C'è qualcosa che vorresti il piano affrontasse? (facoltativo)",
  "virtus.pickToBegin": "Scegli una virtù per iniziare",
  "virtus.buildPlan": "Crea il mio piano di {n} giorni",
  "virtus.yourPlans": "I TUOI PIANI",
  "virtus.theVirtues": "LE VIRTÙ",
  "virtus.goalsEnds": "{done}/{total} obiettivi · termina il {date}",
  // schedule
  "schedule.title": "Orario",
  "schedule.subtitle": "Pianifica la settimana con la Chiesa",
  "schedule.every": "OGNI {day}",
  "schedule.nothing": "Niente in programma per questo giorno.",
  "schedule.upcoming": "PROSSIMO EVENTO SINGOLO",
  "schedule.addToSchedule": "Aggiungi all'orario",
  "schedule.remindersNote": "I promemoria arrivano sull'app iOS/Android compilata, non in questa anteprima web.",
  // schedule editor
  "schedule.addTitle": "Aggiungi all'orario",
  "schedule.editTitle": "Modifica voce",
  "schedule.type": "TIPO",
  "schedule.kind.meal": "Pasto",
  "schedule.kind.workout": "Allenamento",
  "schedule.kind.virtue": "Virtù",
  "schedule.kind.challenge": "Sfida",
  "schedule.kind.custom": "Personalizzato",
  "schedule.titleLabel": "TITOLO",
  "schedule.repeats": "RIPETIZIONE",
  "schedule.weekly": "Settimanale",
  "schedule.oneDate": "Una data",
  "schedule.time": "ORA",
  "schedule.hour": "Ora",
  "schedule.minute": "Minuto",
  "schedule.remindMe": "Ricordamelo",
  "schedule.remindOn": "Una notifica all'ora prevista.",
  "schedule.remindBuild": "I promemoria arrivano sull'app compilata, non nell'anteprima.",
  "schedule.noteOptional": "NOTA (FACOLTATIVA)",
  "schedule.notePlaceholder": "Qualcosa da ricordare…",
  "schedule.activePlan": "PIANO DI VIRTÙ ATTIVO",
  "schedule.enrolledChallenge": "SFIDA ISCRITTA",
  "schedule.noPlans": "Nessun piano di virtù attivo — iniziane uno in Virtus.",
  "schedule.noChallenges": "Non sei ancora iscritto a nessuna sfida.",
  "schedule.addToCalendar": "AGGIUNGI AL TUO CALENDARIO",
  "schedule.calendarHint": "Mettilo su Google o sul calendario del telefono così invierà i promemoria.",
  "schedule.googleCal": "Google Calendar",
  "schedule.appleCal": "Calendario Apple / telefono",
  "schedule.openFull": "Apri l'orario completo",
  "schedule.nothingDay": "Niente in programma per questo giorno.",
  // settings / profile
  "settings.language": "Lingua",
  "settings.languageHint": "Scegli la lingua per l'app e i contenuti IA.",
  "profile.title": "Profilo",
  "profile.defaultName": "Anima fedele",
  "profile.myEvents": "I miei eventi",
  "profile.journal": "Diario",
  "profile.nourishment": "Nutrimento",
  "profile.dietary": "Regime alimentare",
  "profile.allergies": "Allergie / cose da evitare",
  "profile.allergiesPh": "es. noci, crostacei",
  "profile.discipline": "Disciplina",
  "profile.fitnessLevel": "Livello di forma",
  "profile.goal": "Obiettivo",
  "profile.goalPh": "es. costruire resistenza, perdere peso",
  "profile.devotion": "Devozione",
  "profile.focus": "Focus",
  "profile.focusPh": "es. Messa quotidiana, rosario, Liturgia delle Ore",
  "profile.saved": "Salvato",
  "profile.about": "Informazioni",
  "profile.premium": "Sanctus Premium",
  "profile.premiumManage": "Sanctus Premium · Gestisci",
  "profile.shop": "Sanctus Shop",
  "profile.orders": "I miei ordini",
  "profile.support": "Aiuto e supporto",
  "profile.privacy": "Informativa sulla privacy",
  "profile.signOut": "Esci",
  "profile.footer": "Ad maiorem Dei gloriam — per la maggior gloria di Dio.",
  // schedule editor extras
  "schedule.deleteTitle": "Eliminare questa voce?",
  "schedule.deleteMsg": "Sarà rimossa dal tuo orario.",
  "schedule.remindOffTitle": "I promemoria sono disattivati",
  "schedule.remindOffMsg": "Abilita le notifiche per Sanctus nelle Impostazioni per ricevere i promemoria.",
  "schedule.needTitle": "Aggiungi un titolo",
  "schedule.needTitleMsg": "Dai un nome a questa voce.",
  "schedule.pickDay": "Scegli un giorno",
  "schedule.pickDayMsg": "Scegli almeno un giorno della settimana.",
  "schedule.cantSave": "Impossibile salvare",
  "schedule.tryAgain": "Riprova per favore.",
  "schedule.phMeal": "es. Colazione",
  "schedule.phWorkout": "es. Giorno gambe",
  "schedule.phWhat": "Di cosa si tratta?",
  // virtue detail
  "virtus.detail.whatIs": "Che cos'è",
  "virtus.detail.whyMatters": "Perché è importante",
  "virtus.detail.living": "Viverla in ogni stagione",
  "virtus.detail.saints": "Santi che l'hanno vissuta",
  "virtus.detail.prayer": "Una preghiera",
  "virtus.detail.resources": "Risorse per approfondire",
  "virtus.detail.startPlan": "Inizia un piano per questa virtù",
  "virtus.detail.premiumLocked": "Risorse premium",
  "virtus.detail.unlock": "Sblocca con Sanctus Premium",
};

const DICTS: Record<Lang, Dict> = { en, es, it };

function translate(lang: Lang, key: string, vars?: Record<string, string | number>): string {
  let s = DICTS[lang][key] ?? DICTS.en[key] ?? key;
  if (vars) {
    for (const k of Object.keys(vars)) {
      s = s.replace(new RegExp(`\\{${k}\\}`, "g"), String(vars[k]));
    }
  }
  return s;
}

type Ctx = {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
};

const I18nContext = createContext<Ctx>({
  lang: "en",
  setLang: () => undefined,
  t: (k) => translate("en", k),
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then((v) => {
      if (v === "es" || v === "en" || v === "it") {
        _currentLang = v;
        setLangState(v);
      }
    });
  }, []);

  const setLang = useCallback((l: Lang) => {
    _currentLang = l;
    setLangState(l);
    AsyncStorage.setItem(STORAGE_KEY, l).catch(() => undefined);
  }, []);

  const value = useMemo<Ctx>(
    () => ({ lang, setLang, t: (key, vars) => translate(lang, key, vars) }),
    [lang, setLang],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): Ctx {
  return useContext(I18nContext);
}
