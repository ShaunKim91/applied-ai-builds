import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import en from "./en.json";
import ko from "./ko.json";

const DICTS: Record<string, Record<string, string>> = { en, ko };

const LangContext = createContext<{ lang: string; t: (key: string) => string; setLang: (l: string) => void } | null>(null);

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<string>(() => localStorage.getItem("verity-lang") || "en");

  useEffect(() => {
    localStorage.setItem("verity-lang", lang);
  }, [lang]);

  const t = (key: string): string => DICTS[lang]?.[key] ?? DICTS.en[key] ?? key;

  return <LangContext.Provider value={{ lang, t, setLang }}>{children}</LangContext.Provider>;
}

export function useLang() {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useLang must be used within LangProvider");
  return ctx;
}
