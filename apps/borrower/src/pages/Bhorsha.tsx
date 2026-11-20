import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../lib/state";
import { Icon, TLScaffold, useShowError } from "../ui";

type Msg = { text: string; fromUser: boolean };

export default function Bhorsha() {
  const s = useAppState();
  const navigate = useNavigate();
  const showError = useShowError(s);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [completed, setCompleted] = useState(false);
  const [turn, setTurn] = useState(0);
  const [total, setTotal] = useState(12);
  const askedAt = useRef(Date.now());
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const bot = (text: string): Msg => ({ text, fromUser: false });

  const start = async () => {
    try {
      if (!s.consents.has("bhorsha")) {
        await s.api.grantConsent(s.userId!, "bhorsha");
        await s.refreshProfile();
      }
      const q = await s.api.bhorshaStart(s.userId!);
      setSessionId(q.session_id);
      setTurn(q.turn);
      setTotal(q.total_turns);
      setMessages((m) => [...m, bot(s.t("bhorsha_intro")), bot(s.lang === "bn" ? q.question_text : q.english_translation)]);
      askedAt.current = Date.now();
      setBusy(false);
    } catch (e) {
      showError(e, start);
    }
  };

  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    start();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
    if (!completed && !busy) inputRef.current?.focus(); // next answer can be typed straight away
  }, [messages, completed, busy]);

  const send = async () => {
    const text = input.trim();
    if (!text || sessionId == null || busy) return;
    const elapsed = (Date.now() - askedAt.current) / 1000;
    setMessages((m) => [...m, { text, fromUser: true }]);
    setInput("");
    setBusy(true);
    try {
      const r = await s.api.bhorshaAnswer(sessionId, text, elapsed);
      const add: Msg[] = [];
      if (r.acknowledgement != null) add.push(bot(r.acknowledgement));
      if (r.completed === true) {
        setCompleted(true);
        add.push(bot(r.message ?? ""));
      } else {
        setTurn(r.turn);
        add.push(bot(s.lang === "bn" ? r.question_text : r.english_translation));
        askedAt.current = Date.now();
      }
      setMessages((m) => [...m, ...add]);
      setBusy(false);
    } catch (e) {
      setBusy(false);
      showError(e);
    }
  };

  const finish = async () => {
    setBusy(true);
    try {
      await s.api.bhorshaResult(sessionId!);
      navigate("/processing", { replace: true });
    } catch (e) {
      setBusy(false);
      showError(e, finish);
    }
  };

  return (
    <TLScaffold state={s} title={`${s.t("bhorsha_title")} (${turn}/${total})`} bodyClass="body-chat">
      <div className="progress"><div className="progress-fill" style={{ width: `${total === 0 ? 0 : (turn / total) * 100}%` }} /></div>
      <div className="chat" ref={listRef}>
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.fromUser ? "user" : "bot"}`}>{m.text}</div>
        ))}
      </div>
      {completed ? (
        <div className="pad-lg">
          <button className="btn btn-filled" data-testid="bhorsha_finish" disabled={busy} onClick={finish}>{s.t("bhorsha_done")}</button>
        </div>
      ) : (
        <form
          className="chat-input"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <textarea
            ref={inputRef}
            data-testid="bhorsha_input"
            className="input"
            rows={1}
            value={input}
            autoFocus
            enterKeyHint="send"
            placeholder={s.t("type_answer")}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
          />
          <button className="icon-btn" type="submit" data-testid="bhorsha_send" title={s.t("send")} aria-label={s.t("send")} disabled={busy}>
            <Icon name="send" color="var(--teal-dark)" />
          </button>
        </form>
      )}
    </TLScaffold>
  );
}
