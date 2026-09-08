import { useEffect, useState } from "react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import { useLang } from "../i18n";

interface CatEvent {
  id: number;
  name: string;
  event_type: string;
  region: string;
  occurred_on: string;
  description: string;
}

const TYPES = ["hail", "wind", "flood", "wildfire", "other"];

export default function CatEvents() {
  const { t } = useLang();
  const [events, setEvents] = useState<CatEvent[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", event_type: "hail", region: "", occurred_on: "", description: "" });
  const [sessionsByEvent, setSessionsByEvent] = useState<Record<number, { id: number; title: string }[]>>({});

  const load = () => api.get<CatEvent[]>("/api/cat-events").then(setEvents);
  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    if (!form.name || !form.occurred_on) return;
    await api.post("/api/cat-events", form);
    setForm({ name: "", event_type: "hail", region: "", occurred_on: "", description: "" });
    setShowForm(false);
    load();
  };

  const viewSessions = async (id: number) => {
    const rows = await api.get<{ id: number; title: string }[]>(`/api/cat-events/${id}/sessions`);
    setSessionsByEvent((prev) => ({ ...prev, [id]: rows }));
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-2xl mb-1">{t("catEvents.title")}</h1>
          <p style={{ color: "var(--text-secondary)" }}>{t("catEvents.subtitle")}</p>
        </div>
        <button className="btn-primary px-4 py-2" onClick={() => setShowForm((s) => !s)}>
          + {t("catEvents.new")}
        </button>
      </div>

      {showForm && (
        <div className="card p-4 mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          <input
            className="px-3 py-2 rounded-ledger-sm border"
            style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
            placeholder={t("catEvents.name")}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <select
            className="px-3 py-2 rounded-ledger-sm border"
            style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
            value={form.event_type}
            onChange={(e) => setForm({ ...form, event_type: e.target.value })}
          >
            {TYPES.map((t2) => (
              <option key={t2} value={t2}>
                {t2}
              </option>
            ))}
          </select>
          <input
            className="px-3 py-2 rounded-ledger-sm border"
            style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
            placeholder={t("catEvents.region")}
            value={form.region}
            onChange={(e) => setForm({ ...form, region: e.target.value })}
          />
          <input
            type="date"
            className="px-3 py-2 rounded-ledger-sm border"
            style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
            value={form.occurred_on}
            onChange={(e) => setForm({ ...form, occurred_on: e.target.value })}
          />
          <textarea
            className="px-3 py-2 rounded-ledger-sm border md:col-span-2"
            style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
            placeholder={t("catEvents.description")}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <button className="btn-primary py-2 md:col-span-2" onClick={create}>
            {t("catEvents.create")}
          </button>
        </div>
      )}

      <div className="mt-6 space-y-3">
        {events.length === 0 && <EmptyState>{t("catEvents.empty")}</EmptyState>}
        {events.map((ev) => (
          <div key={ev.id} className="card p-4">
            <div className="flex justify-between items-start">
              <div>
                <div className="font-display font-bold">{ev.name}</div>
                <div className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
                  {ev.event_type} · {ev.region} · {ev.occurred_on}
                </div>
              </div>
              <button className="btn-secondary text-xs px-3 py-1" onClick={() => viewSessions(ev.id)}>
                {t("catEvents.viewSessions")}
              </button>
            </div>
            {ev.description && (
              <p className="text-sm mt-2" style={{ color: "var(--text-secondary)" }}>
                {ev.description}
              </p>
            )}
            {sessionsByEvent[ev.id] && (
              <ul className="mt-2 text-sm list-disc pl-5">
                {sessionsByEvent[ev.id].length === 0 && <li style={{ color: "var(--text-muted)" }}>—</li>}
                {sessionsByEvent[ev.id].map((s) => (
                  <li key={s.id}>{s.title}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
