"use client";

import { ExternalLink, Star, Copy, Check, ThumbsUp, ThumbsDown, Minus, Trash2 } from "lucide-react";
import { useState } from "react";
import {
  cn,
  getSentimentConfig,
  getSourceColor,
  getSourceLabel,
  getLanguageLabel,
  formatRelativeDate,
  getInitials,
} from "@/lib/utils";
import type { Mention } from "@/lib/supabase";

interface MentionCardProps {
  mention: Mention;
  className?: string;
  compact?: boolean;
}

export function MentionCard({ mention, className, compact = false }: MentionCardProps) {
  const [copied, setCopied] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [currentSentiment, setCurrentSentiment] = useState(mention.sentiment_label);
  const [showRejectMenu, setShowRejectMenu] = useState(false);

  const sourceSlug = mention.sources?.slug ?? "";
  const sourceName = getSourceLabel(sourceSlug);
  const sourceColor = getSourceColor(sourceSlug);
  const initials   = getInitials(mention.author_name);
  const langLabel  = getLanguageLabel(mention.language);

  // Limpiador de texto (HTML Entities)
  const cleanText = (text: string) => {
    if (!text) return "";
    return text
      .replace(/&nbsp;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&quot;/g, '"')
      .replace(/&apos;/g, "'")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/\s\s+/g, ' '); // Remover espacios dobles
  };

  const handleUpdateSentiment = async (newLabel: any) => {
    if (newLabel === currentSentiment) return;
    setIsUpdating(true);
    try {
      const { updateMentionSentiment } = await import("@/lib/supabase");
      const ok = await updateMentionSentiment(mention.id, newLabel);
      if (ok) {
        setCurrentSentiment(newLabel);
      }
    } catch (err) {
      console.error("Error updating sentiment:", err);
    } finally {
      setIsUpdating(false);
    }
  };

  const sentimentConfig = getSentimentConfig(currentSentiment);

  // Texto truncado del dominio para mostrar en el botón "Ver fuente"
  const sourceUrlLabel = (() => {
    try {
      if (!mention.source_url) return null;
      const url = new URL(mention.source_url);
      return url.hostname.replace("www.", "");
    } catch {
      return mention.source_url?.substring(0, 30);
    }
  })();

  const handleCopyUrl = async () => {
    if (!mention.source_url) return;
    try {
      await navigator.clipboard.writeText(mention.source_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {/* silenciar */ }
  };

  return (
    <div
      className={cn(
        "bg-white border border-slate-200 rounded-xl shadow-sm transition-all duration-200 hover:shadow-md max-w-lg",
        "animate-fade-in flex flex-col",
        className
      )}
    >
      {/* ── Header ── */}
      <div className={cn("flex items-start gap-3", compact ? "p-3" : "p-4")}>
        {/* Avatar */}
        <div className="flex-shrink-0">
          {mention.author_avatar_url ? (
            <img
              src={mention.author_avatar_url}
              alt={mention.author_name ?? ""}
              className="h-9 w-9 rounded-full object-cover border"
            />
          ) : (
            <div
              className="h-9 w-9 rounded-full flex items-center justify-center text-white text-xs font-semibold"
              style={{ backgroundColor: sourceColor }}
            >
              {initials}
            </div>
          )}
        </div>

        {/* Meta */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center flex-wrap gap-1.5 mb-0.5">
            <span className="font-semibold text-sm text-foreground truncate">
              {mention.author_name ?? "Anónimo"}
            </span>

            {/* Fuente */}
            <span
              className="text-xs px-2 py-0.5 rounded font-medium border"
              style={{
                backgroundColor: `${sourceColor}12`,
                color: sourceColor,
                borderColor: `${sourceColor}30`,
              }}
            >
              {sourceName}
            </span>

            {/* Entidad */}
            <span className="text-xs px-2 py-0.5 rounded font-medium border bg-slate-100 text-slate-700 border-slate-200">
              {mention.entities?.name ?? "General"}
            </span>

            {/* Idioma */}
            <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-mono border">
              {langLabel}
            </span>

            {/* Revisión Humana Badge */}
            {(mention.confidence_score ?? 1) < 0.75 && (
              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-50 text-amber-600 font-bold border border-amber-200 uppercase tracking-tight flex items-center gap-1 shadow-sm">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
                Requiere Revisión
              </span>
            )}
          </div>

          {/* Fecha */}
          <p className="text-xs text-muted-foreground">
            {formatRelativeDate(mention.published_at ?? mention.collected_at)}
          </p>
        </div>

        {/* Sentimiento (Manual Selector) */}
        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center gap-1">
            <div className="flex items-center gap-1 bg-slate-50 border rounded-lg p-0.5">
              {(['positive', 'neutral', 'negative'] as const).map((label) => (
                <button
                  key={label}
                  onClick={() => handleUpdateSentiment(label)}
                  disabled={isUpdating}
                  title={`Cambiar a ${label}`}
                  className={cn(
                    "w-6 h-6 rounded-md flex items-center justify-center transition-all",
                    currentSentiment === label 
                      ? "bg-white shadow-sm border scale-110" 
                      : "text-slate-400 hover:text-slate-600 grayscale opacity-60 hover:opacity-100"
                  )}
                >
                  {label === 'positive' && <ThumbsUp className="h-3 w-3 text-emerald-600" />}
                  {label === 'neutral' && <Minus className="h-3 w-3 text-slate-600" />}
                  {label === 'negative' && <ThumbsDown className="h-3 w-3 text-red-600" />}
                </button>
              ))}
            </div>
            
            {/* Botón de rechazo / irrelevante */}
            <div className="relative">
              {showRejectMenu && (
                <div className="absolute right-0 top-8 w-48 bg-white border shadow-lg rounded-md z-10 p-1 flex flex-col gap-1 text-sm animate-in fade-in zoom-in-95">
                  <div className="px-2 py-1 text-xs font-semibold text-slate-500 border-b mb-1">
                    Razón de eliminación:
                  </div>
                  {[
                    "Spam o Promoción",
                    "No relacionado a CZFS",
                    "Idioma o región incorrecta",
                    "Contenido ofensivo",
                    "Otro"
                  ].map(reason => (
                    <button
                      key={reason}
                      onClick={async (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setShowRejectMenu(false);
                        setIsUpdating(true);
                        try {
                          const { rejectMention } = await import("@/lib/supabase");
                          const ok = await rejectMention(mention.id, reason);
                          if (ok) {
                            window.location.reload();
                          } else {
                            alert("Error eliminando mención");
                          }
                        } catch (err) {
                          console.error(err);
                          alert("Error al procesar la eliminación");
                        } finally {
                          setIsUpdating(false);
                        }
                      }}
                      className="text-left px-2 py-1.5 hover:bg-slate-100 rounded text-slate-700 hover:text-red-600 transition-colors"
                    >
                      {reason}
                    </button>
                  ))}
                  <button 
                    onClick={() => setShowRejectMenu(false)}
                    className="text-center px-2 py-1.5 mt-1 text-xs text-slate-400 hover:text-slate-600 border-t"
                  >
                    Cancelar
                  </button>
                </div>
              )}
              <button
                onClick={() => setShowRejectMenu(!showRejectMenu)}
                disabled={isUpdating}
                title="Marcar como irrelevante (Aprender de este error)"
                className="w-6 h-6 rounded-md flex items-center justify-center transition-all text-slate-400 hover:text-red-500 hover:bg-red-50"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          <span 
            className="text-[10px] font-bold uppercase tracking-wider"
            style={{ color: sentimentConfig.color }}
          >
            {sentimentConfig.label}
          </span>
        </div>
      </div>

      {/* ── Estrellas (Google Reviews) ── */}
      {mention.star_rating != null && (
        <div className="flex items-center gap-0.5 px-4 pb-1.5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Star
              key={i}
              className={cn(
                "h-3.5 w-3.5",
                i < mention.star_rating!
                  ? "fill-yellow-400 text-yellow-400"
                  : "fill-gray-200 text-gray-200"
              )}
            />
          ))}
          <span className="text-xs text-muted-foreground ml-1.5 font-medium">
            {mention.star_rating}/5
          </span>
        </div>
      )}

      <div className={cn("px-5 pb-4 flex-1", compact && "px-4 pb-3")}>
        <p
          className={cn(
            "text-[15px] text-slate-700 leading-relaxed",
            compact && "line-clamp-5 text-sm"
          )}
        >
          {cleanText(mention.text_original)}
        </p>
      </div>

      {/* ── Pie: Confianza NLP + Enlace a fuente original ── */}
      <div className="px-4 py-2.5 border-t bg-muted/20 rounded-b-xl flex items-center justify-between gap-3 flex-wrap">

        {/* Confianza del análisis */}
        {mention.confidence_score != null && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Confianza:</span>
            <div className="w-14 h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.round(mention.confidence_score * 100)}%`,
                  backgroundColor: sentimentConfig.color,
                }}
              />
            </div>
            <span className="text-xs text-muted-foreground tabular-nums">
              {Math.round(mention.confidence_score * 100)}%
            </span>
          </div>
        )}

        {/* Enlace directo a la publicación original */}
        <div className="flex items-center gap-1.5 ml-auto">
          {mention.source_url && (
            <>
              {/* Copiar URL */}
              <button
                onClick={handleCopyUrl}
                title="Copiar enlace al portapapeles"
                className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                {copied
                  ? <Check className="h-3.5 w-3.5 text-green-600" />
                  : <Copy className="h-3.5 w-3.5" />
                }
              </button>

              {/* Abrir fuente */}
              <a
                href={mention.source_url}
                target="_blank"
                rel="noopener noreferrer"
                title={mention.source_url}
                className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              >
                {sourceUrlLabel ?? "Abrir fuente"}
                <ExternalLink className="h-3 w-3 flex-shrink-0" />
              </a>
            </>
          )}

          {!mention.source_url && (
            <span className="text-xs text-muted-foreground italic">
              Sin enlace disponible
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Skeleton
// ============================================================
export function MentionCardSkeleton() {
  return (
    <div className="bg-card border rounded-xl shadow-sm p-4">
      <div className="flex items-start gap-3 mb-3">
        <div className="skeleton h-9 w-9 rounded-full" />
        <div className="flex-1 space-y-1.5">
          <div className="skeleton h-4 w-32 rounded" />
          <div className="skeleton h-3 w-20 rounded" />
        </div>
        <div className="skeleton h-6 w-16 rounded" />
      </div>
      <div className="space-y-1.5 mb-3">
        <div className="skeleton h-3 w-full rounded" />
        <div className="skeleton h-3 w-5/6 rounded" />
        <div className="skeleton h-3 w-4/6 rounded" />
      </div>
      <div className="flex justify-between items-center border-t pt-2.5">
        <div className="skeleton h-3 w-28 rounded" />
        <div className="skeleton h-3 w-20 rounded" />
      </div>
    </div>
  );
}
