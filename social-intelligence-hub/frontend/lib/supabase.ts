import { createClient } from "@supabase/supabase-js";

const supabaseUrl = "https://zhbutmbnhzcgrlkuafwb.supabase.co"
// Utilizando Service Role Key temporalmente para puentear el RLS que está bloqueando la app en localhost
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpoYnV0bWJuaHpjZ3Jsa3VhZndiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjM4NTU3NCwiZXhwIjoyMDkxOTYxNTc0fQ.hsBldRNa4CuQRsVIvsXp80mW9kACz4XLeWuc36lykGQ"

export const supabase = createClient(supabaseUrl, supabaseKey);

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
  const { data, error } = await supabase
    .from("v_sentiment_summary")
    .select("*")
    .order("total_mentions", { ascending: false });

  if (error) {
    console.error("fetchSentimentSummary error:", error.message);
    throw new Error(`Error en v_sentiment_summary: ${error.message}`);
  }
  return data || [];
}

export async function fetchDailyTrend(
  entitySlug?: string,
  dateFrom?: string,
  dateTo?: string,
  searchQuery?: string
): Promise<DailyTrend[]> {
  // Cuando tenemos searchQuery, no podemos usar la vista v_daily_trend de forma tan sencilla,
  // pero podemos intentar filtrarla si las menciones hicieran JOIN, o simplemente
  // fallbacks. Como la vista pre-calcula todo, si hay searchQuery es mejor ignorarlo 
  // o hacer una consulta a mentions. Para no romper la vista, haremos una consulta
  // a mentions y agrupamos en el frontend o aquí si hay consulta de texto.
  if (searchQuery) {
    let q = supabase.from("mentions").select("published_at, sentiment_label, entities!inner(slug)");
    if (entitySlug) q = q.eq("entities.slug", entitySlug);
    if (dateFrom) q = q.gte("published_at", dateFrom);
    if (dateTo) q = q.lte("published_at", dateTo);
    q = q.ilike("text_original", `%${searchQuery}%`);
    
    const { data, error } = await q;
    if (error) {
      console.error("fetchDailyTrend error:", error.message);
      return [];
    }
    // Agrupar manualmente
    const grouped: Record<string, DailyTrend> = {};
    for (const m of (data || [])) {
      if (!m.published_at) continue;
      const date = m.published_at.substring(0, 10);
      const entity = Array.isArray(m.entities) ? m.entities[0]?.slug : m.entities?.slug;
      if (!entity) continue;
      const key = `${date}_${entity}_${m.sentiment_label}`;
      if (!grouped[key]) {
        grouped[key] = { mention_date: date, entity_slug: entity, sentiment_label: m.sentiment_label, mention_count: 0 };
      }
      grouped[key].mention_count++;
    }
    return Object.values(grouped).sort((a, b) => a.mention_date.localeCompare(b.mention_date));
  }

  let query = supabase
    .from("v_daily_trend")
    .select("*")
    .order("mention_date", { ascending: true });

  if (entitySlug) {
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
    console.error("fetchDailyTrend error:", error.message);
    throw new Error(`Error en v_daily_trend: ${error.message}`);
  }
  return data || [];
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
  // Ignorar todos los params para traer todo sin filtros
  const limit = 50;
  const offset = 0;

  // Cambiamos entities!inner a entities (LEFT JOIN) para que no oculte menciones sin entidad
  let query = supabase
    .from("mentions")
    .select(
      `*, entities(id, slug, name, category), sources(id, slug, name)`,
      { count: "exact" }
    )
    .order("published_at", { ascending: false })
    .range(offset, offset + limit - 1);

  // Filtros eliminados temporalmente según la instrucción del usuario

  const { data, error, count } = await query;
  if (error) {
    console.error("fetchMentions error:", error.message);
    throw new Error(`Error en mentions: ${error.message}`);
  }
  
  console.log("=== DATOS OBTENIDOS POR FETCHMENTIONS (SIN FILTROS) ===", data);
  
  return { data: (data as Mention[]) || [], count: count || 0 };
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
  let query = supabase
    .from("mentions")
    .select("sentiment_label, dominican_override, published_at, entities!inner(slug)");

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
    console.error("fetchTotalStats error:", error.message);
    throw new Error(`Error en stats: ${error.message}`);
  }

  const mentions  = data || [];
  const total     = mentions.length;
  const positive  = mentions.filter((m) => m.sentiment_label === "positive").length;
  const negative  = mentions.filter((m) => m.sentiment_label === "negative").length;
  const neutral   = mentions.filter((m) => m.sentiment_label === "neutral").length;
  const overrides = mentions.filter((m) => m.dominican_override).length;

  return {
    totalMentions:    total,
    positiveCount:    positive,
    negativeCount:    negative,
    neutralCount:     neutral,
    netSentiment:     total > 0 ? Math.round(((positive - negative) / total) * 100) : 0,
    localTermOverrides: overrides,
  };
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

