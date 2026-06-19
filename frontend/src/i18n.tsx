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

export type Lang = "en" | "es";
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
};

const DICTS: Record<Lang, Dict> = { en, es };

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
      if (v === "es" || v === "en") {
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
