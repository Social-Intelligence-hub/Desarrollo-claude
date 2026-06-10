import { createClient } from "@supabase/supabase-js";

// ============================================================
// Cliente público de Supabase — SOLO anon key.
// La Service Role Key fue retirada del cliente (saneamiento de seguridad F0):
// exponerla daría acceso total a la BD saltando RLS. Las escrituras viven del
// lado del scraper (service role en servidor / GitHub Actions). El frontend solo
// lee tablas y vistas con política de lectura pública (RLS — migración 005).
// ============================================================
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Faltan NEXT_PUBLIC_SUPABASE_URL o NEXT_PUBLIC_SUPABASE_ANON_KEY. " +
    "Defínelas en frontend/.env.local (ver .env.example) y en las env vars de Vercel."
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// ============================================================
// Connection test helper (used by health indicator in footer)
// ============================================================
export async function testConnection(): Promise<{ ok: boolean; error?: string }> {
  try {
    const { error } = await supabase.from("entities").select("id").limit(1);
    if (error) return { ok: false, error: error.message };
    return { ok: true };
  } catch (e: any) {
    return { ok: false, error: e?.message ?? "Error desconocido" };
  }
}

// ============================================================
// Types
// ============================================================

export type SentimentLabel = "positive" | "negative" | "neutral" | "mixed";

export interface Entity {
  id: string;
  slug: string;
  name: string;
  category: string;
  keywords: string[];
  anti_keywords: string[];
  description?: string;
  active: boolean;
}

export interface Source {
  id: string;
  slug: string;
  name: string;
  icon_url?: string;
}

export interface Mention {
  id: string;
  entity_id: string;
  source_id: string;
  text_original: string;
  author_name?: string;
  author_avatar_url?: string;
  source_url?: string;
  star_rating?: number;
  sentiment_label: SentimentLabel;
  sentiment_score?: {
    positive: number;
    negative: number;
    neutral: number;
  };
  confidence_score?: number;
  dominican_override: boolean;
  dominican_term_found?: string;
  published_at?: string;
  collected_at: string;
  language?: string;
  is_demo?: boolean;
  entities?: Entity;
  sources?: Source;
}

export interface SentimentSummary {
  entity_slug: string;
  entity_name: string;
  category: string;
  total_mentions: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  mixed_count: number;
  positive_pct: number;
  net_sentiment_score: number;
  last_updated?: string;
}

export interface DailyTrend {
  mention_date: string;
  entity_slug: string;
  sentiment_label: SentimentLabel;
  mention_count: number;
}

// ============================================================
// Query helpers
// ============================================================

export async function fetchSentimentSummary(): Promise<SentimentSummary[]> {
  try {
    const { data, error } = await supabase
      .from("v_sentiment_summary")
      .select("*")
      .order("total_mentions", { ascending: false });

    if (error) {
      console.error("Supabase Error (v_sentiment_summary):", error);
      return [];
    }
    return data || [];
  } catch (e) {
    console.error("fetchSentimentSummary Exception:", e);
    return [];
  }
}

export async function fetchDailyTrend(
  entitySlug?: string,
  dateFrom?: string,
  dateTo?: string,
  searchQuery?: string
): Promise<DailyTrend[]> {
  try {
    // Si hay búsqueda de texto, calculamos tendencia a mano desde mentions
    if (searchQuery) {
      let q = supabase.from("mentions").select("published_at, sentiment_label, entities!inner(slug)");
      if (entitySlug && entitySlug !== "all") q = q.eq("entities.slug", entitySlug);
      if (dateFrom) q = q.gte("published_at", dateFrom);
      if (dateTo) q = q.lte("published_at", dateTo);
      q = q.ilike("text_original", `%${searchQuery}%`);
      
      const { data, error } = await q;
      if (error) {
        console.error("Error manual trend:", error);
        return [];
      }
      
      const grouped: Record<string, DailyTrend> = {};
      (data || []).forEach((m: any) => {
        if (!m.published_at) return;
        const date = m.published_at.substring(0, 10);
        const entity = m.entities?.slug || "unknown";
        const key = `${date}_${entity}_${m.sentiment_label}`;
        if (!grouped[key]) {
          grouped[key] = { mention_date: date, entity_slug: entity, sentiment_label: m.sentiment_label, mention_count: 0 };
        }
        grouped[key].mention_count++;
      });
      return Object.values(grouped).sort((a, b) => a.mention_date.localeCompare(b.mention_date));
    }

    // Caso estándar: usar la vista
    let query = supabase
      .from("v_daily_trend")
      .select("*")
      .order("mention_date", { ascending: true });

    if (entitySlug && entitySlug !== "all") {
      query = query.eq("entity_slug", entitySlug);
    }
    if (dateFrom) {
      query = query.gte("mention_date", dateFrom.substring(0, 10));
    }
    if (dateTo) {
      query = query.lte("mention_date", dateTo.substring(0, 10));
    }

    const { data, error } = await query;
    if (error) {
      console.error("Supabase Error (v_daily_trend):", error);
      return [];
    }
    return data || [];
  } catch (e) {
    console.error("fetchDailyTrend Exception:", e);
    return [];
  }
}

export async function fetchMentions(params: {
  entitySlug?: string;
  sentiment?: SentimentLabel | "all";
  sourceSlug?: string;
  searchQuery?: string;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
  offset?: number;
}): Promise<{ data: Mention[]; count: number }> {
  try {
    const {
      entitySlug,
      sentiment,
      sourceSlug,
      searchQuery,
      dateFrom,
      dateTo,
      limit = 20,
      offset = 0,
    } = params;

    const selectStr = `*, entities!inner(id, slug, name, category), sources(id, slug, name)`;
    
    let query = supabase
      .from("mentions")
      .select(selectStr, { count: "exact" })
      .order("published_at", { ascending: false })
      .range(offset, offset + limit - 1);

    if (entitySlug && entitySlug !== "all") {
      query = query.eq("entities.slug", entitySlug);
    }

    if (sentiment && sentiment !== "all") {
      query = query.eq("sentiment_label", sentiment);
    }

    if (sourceSlug && sourceSlug !== "all") {
      // Find source ID first to avoid !inner dynamic join issues in PostgREST
      const { data: sourceObj } = await supabase.from("sources").select("id").eq("slug", sourceSlug).single();
      if (sourceObj) {
        query = query.eq("source_id", sourceObj.id);
      } else {
        // If source not found, return empty
        return { data: [], count: 0 };
      }
    }

    if (searchQuery) {
      query = query.ilike("text_original", `%${searchQuery}%`);
    }

    if (dateFrom) {
      query = query.gte("published_at", dateFrom);
    }

    if (dateTo) {
      query = query.lte("published_at", dateTo);
    }

    const { data, error, count } = await query;
    if (error) {
      console.error("Supabase Error (fetchMentions):", error);
      throw error;
    }
    
    console.log("fetchMentions query result:", { count, dataLength: data?.length, sourceSlug });
    return { data: (data as Mention[]) || [], count: count || 0 };
  } catch (e: any) {
    console.error("fetchMentions Exception:", e.message);
    return { data: [], count: 0 };
  }
}

export async function fetchEntities(): Promise<Entity[]> {
  const { data, error } = await supabase
    .from("entities")
    .select("*")
    .eq("active", true)
    .order("name");

  if (error) {
    console.error("fetchEntities error:", error.message);
    throw new Error(`Error en entities: ${error.message}`);
  }
  return data || [];
}

export async function fetchSources(): Promise<Source[]> {
  const { data, error } = await supabase
    .from("sources")
    .select("id, slug, name, icon_url")
    .eq("active", true);

  if (error) {
    console.error("fetchSources error:", error.message);
    throw new Error(`Error en sources: ${error.message}`);
  }
  return data || [];
}

export async function fetchTotalStats(
  dateFrom?: string,
  dateTo?: string,
  entitySlug?: string,
  searchQuery?: string
): Promise<{
  totalMentions: number;
  positiveCount: number;
  negativeCount: number;
  neutralCount: number;
  netSentiment: number;
  localTermOverrides: number;
}> {
  try {
    // Para las stats de los KPI, hacemos un conteo más simple
    let query = supabase
      .from("mentions")
      .select("sentiment_label, dominican_override, entities!inner(slug)");

    if (dateFrom) query = query.gte("published_at", dateFrom);
    if (dateTo)   query = query.lte("published_at", dateTo);
    if (entitySlug && entitySlug !== "all") {
      query = query.eq("entities.slug", entitySlug);
    }
    if (searchQuery) {
      query = query.ilike("text_original", `%${searchQuery}%`);
    }

    const { data, error } = await query;
    if (error) {
      console.error("Supabase Error (fetchTotalStats):", error);
      return { totalMentions: 0, positiveCount: 0, negativeCount: 0, neutralCount: 0, netSentiment: 0, localTermOverrides: 0 };
    }

    const mentions  = data || [];
    const total     = mentions.length;
    const positive  = mentions.filter((m: any) => m.sentiment_label === "positive").length;
    const negative  = mentions.filter((m: any) => m.sentiment_label === "negative").length;
    const neutral   = mentions.filter((m: any) => m.sentiment_label === "neutral").length;
    const overrides = mentions.filter((m: any) => m.dominican_override).length;

    return {
      totalMentions:    total,
      positiveCount:    positive,
      negativeCount:    negative,
      neutralCount:     neutral,
      netSentiment:     total > 0 ? Math.round(((positive - negative) / total) * 100) : 0,
      localTermOverrides: overrides,
    };
  } catch (e) {
    console.error("fetchTotalStats Exception:", e);
    return { totalMentions: 0, positiveCount: 0, negativeCount: 0, neutralCount: 0, netSentiment: 0, localTermOverrides: 0 };
  }
}

export async function updateMentionSentiment(id: string, label: SentimentLabel): Promise<boolean> {
  try {
    const { error } = await supabase
      .from("mentions")
      .update({ 
        sentiment_label: label,
        confidence_score: 1.0, // Al ser manual, la confianza es total
        updated_at: new Date().toISOString()
      })
      .eq("id", id);

    if (error) {
      console.error("Error updating sentiment:", error);
      return false;
    }
    return true;
  } catch (e) {
    console.error("updateMentionSentiment Exception:", e);
    return false;
  }
}

export async function fetchEntityBySlug(slug: string): Promise<Entity | null> {
  const { data, error } = await supabase
    .from("entities")
    .select("*")
    .eq("slug", slug)
    .maybeSingle();

  if (error) {
    console.error("fetchEntityBySlug error:", error.message);
    return null;
  }
  return data;
}

export async function fetchSourceStats(entitySlug: string): Promise<Array<{ source_name: string, count: number }>> {
  const { data, error } = await supabase
    .from("mentions")
    .select("sources!inner(name), entities!inner(slug)")
    .eq("entities.slug", entitySlug);

  if (error) {
    console.error("fetchSourceStats error:", error.message);
    return [];
  }

  const counts: Record<string, number> = {};
  (data || []).forEach((m: any) => {
    const name = m.sources?.name || "Desconocido";
    counts[name] = (counts[name] || 0) + 1;
  });

  return Object.entries(counts)
    .map(([source_name, count]) => ({ source_name, count }))
    .sort((a, b) => b.count - a.count);
}
export async function rejectMention(id: string, reason: string): Promise<boolean> {
  try {
    // 1. Obtener los detalles de la mención antes de borrarla
    const { data: mention, error: selectError } = await supabase
      .from("mentions")
      .select("text_original")
      .eq("id", id)
      .single();
      
    if (selectError) {
      console.error("Error fetching mention for rejection:", selectError);
    }

    // 2. Si hay una razón y encontramos el texto, lo guardamos para la "lista negra"
    if (mention && reason) {
      const { error: insertError } = await supabase
        .from("relevance_feedback")
        .insert({
          mention_id: id,
          text_original: mention.text_original,
          reason: reason
        });
        
      if (insertError) {
        console.warn("No se pudo guardar feedback:", insertError);
      }
    }

    // 3. Borrar la mención
    const { error } = await supabase
      .from("mentions")
      .delete()
      .eq("id", id);

    if (error) {
      console.error("Error deleting mention:", error);
      return false;
    }

    return true;
  } catch (e) {
    console.error("rejectMention Exception:", e);
    return false;
  }
}
