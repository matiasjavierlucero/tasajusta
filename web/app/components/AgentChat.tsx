"use client";

import { useState, useRef, useEffect } from "react";

type Message = { role: "user" | "assistant"; content: string };

const SUGERENCIAS = [
  "¿Qué oportunidades hay hoy?",
  "Busco un Toyota con menos de 80k km",
  "¿Cuánto vale un Gol 2018 con 60k km en Córdoba?",
  "Top 5 autos más subvaluados",
];

export default function AgentChat() {
  const [open,      setOpen]      = useState(false);
  const [messages,  setMessages]  = useState<Message[]>([]);
  const [input,     setInput]     = useState("");
  const [loading,   setLoading]   = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, open]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: "user", content: text.trim() };
    const nextMessages     = [...messages, userMsg];

    setMessages(nextMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/agent", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ messages: nextMessages }),
      });

      if (!res.ok) throw new Error("error");

      const data = await res.json();
      setMessages([...nextMessages, { role: "assistant", content: data.response }]);
    } catch {
      setMessages([...nextMessages, {
        role:    "assistant",
        content: "Tuve un problema para procesar tu consulta. ¿Podés intentarlo de nuevo o reformular la pregunta?",
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  const isEmpty = messages.length === 0;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">

      {/* Panel del chat */}
      {open && (
        <div className="w-[360px] sm:w-[400px] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden"
          style={{ height: 520 }}>

          {/* Header */}
          <div className="px-4 py-3 bg-brand-500 flex items-center gap-3 flex-shrink-0">
            <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              IA
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white leading-none">Asesor TasaJusta</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-sage-400 animate-pulse" />
                <span className="text-xs text-brand-100">En línea</span>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-white/70 hover:text-white transition-colors p-1"
              aria-label="Cerrar"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5">
            {isEmpty ? (
              <div className="h-full flex flex-col items-center justify-center text-center px-2">
                <p className="text-slate-400 text-xs mb-4">
                  Preguntame sobre autos, oportunidades o cotizaciones
                </p>
                <div className="grid grid-cols-1 gap-1.5 w-full">
                  {SUGERENCIAS.map((s) => (
                    <button
                      key={s}
                      onClick={() => sendMessage(s)}
                      className="text-left text-xs px-3 py-2 rounded-lg border border-slate-200
                        text-slate-600 hover:border-brand-400 hover:text-brand-600 hover:bg-brand-50
                        transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div
                      className={`max-w-[85%] rounded-2xl px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap ${
                        msg.role === "user"
                          ? "bg-brand-500 text-white rounded-br-sm"
                          : "bg-slate-100 text-slate-800 rounded-bl-sm"
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-3 py-2.5 flex gap-1 items-center">
                      {[0, 150, 300].map((delay) => (
                        <span
                          key={delay}
                          className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"
                          style={{ animationDelay: `${delay}ms` }}
                        />
                      ))}
                    </div>
                  </div>
                )}

              </>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="px-3 py-2.5 border-t border-slate-200 flex gap-2 flex-shrink-0">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Escribí tu consulta..."
              disabled={loading}
              className="flex-1 text-xs px-3 py-2 rounded-xl border border-slate-300
                focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20
                disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="px-3 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 active:bg-brand-700
                text-white text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed
                transition-colors flex-shrink-0"
            >
              Enviar
            </button>
          </form>
        </div>
      )}

      {/* Botón flotante */}
      <div className="relative">
        {/* Ping solo cuando está cerrado */}
        {!open && (
          <span className="absolute inset-0 rounded-full bg-brand-400 animate-ping opacity-30 pointer-events-none" />
        )}
        <button
          onClick={() => setOpen(o => !o)}
          className="relative w-14 h-14 rounded-full bg-brand-500 hover:bg-brand-600 active:bg-brand-700
            shadow-lg text-white flex items-center justify-center transition-all
            hover:scale-105 active:scale-95"
          aria-label="Abrir asesor IA"
        >
          {open ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          ) : (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}
