import React, { createContext, useContext, useMemo, useState } from "react";

import en from "./en.json";
import ko from "./ko.json";

type Lang = "en" | "ko";
const DICTS: Record<Lang, Record<string, string>> = { en, ko };
const STORAGE_KEY = "cradle.lang";

interface I18nCtx {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string) => string;
}

const Ctx = createContext<I18nCtx | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      return saved === "ko" ? "ko" : "en"; // app defaults to ENGLISH
    } catch {
      return "en";
    }
  });

  const setLang = (l: Lang) => {
    setLangState(l);
    try {
      window.localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* ignore */
    }
  };

  const t = useMemo(() => {
    const dict = DICTS[lang];
    return (key: string) => dict[key] ?? key;
  }, [lang]);

  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}

export function useI18n() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
