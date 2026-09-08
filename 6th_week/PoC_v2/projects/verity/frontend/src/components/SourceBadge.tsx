import { useLang } from "../i18n";

export default function SourceBadge({ tier }: { tier: "primary" | "secondary" | "unverified" }) {
  const { t } = useLang();
  const cls = tier === "primary" ? "badge-primary-source" : tier === "secondary" ? "badge-secondary-source" : "badge-unverified-source";
  const label = tier === "primary" ? t("research.trustPrimary") : tier === "secondary" ? t("research.trustSecondary") : t("research.trustUnverified");
  return <span className={`badge ${cls}`}>{label}</span>;
}
