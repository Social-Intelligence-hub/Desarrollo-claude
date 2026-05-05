"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import {
  BarChart2, Bell, RefreshCw, Globe,
  ThumbsUp, ThumbsDown, Minus, AlertTriangle, Filter,
  Wifi, WifiOff, Zap, ArrowUpRight, BarChart3, FileText, Download
} from "lucide-react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { KpiCard, NetSentimentCard } from "@/components/KpiCard";
import { TrendChart, SentimentDonut, EntitiesComparisonChart } from "@/components/SentimentChart";
import { MentionCard, MentionCardSkeleton } from "@/components/MentionCard";
import { SearchBar, FilterChips } from "@/components/SearchBar";
import { DateRangeFilter } from "@/components/DateRangeFilter";
import {
  cn, formatShortDate, formatNumber,
  resolveDateRange, type DateRange,
} from "@/lib/utils";
import type { CapexInterpretation } from "@/components/DisambiguationModal";
import {
  fetchSentimentSummary,
  fetchDailyTrend,
  fetchMentions,
  fetchTotalStats,
  testConnection,
  type SentimentSummary,
  type DailyTrend,
  type Mention,
  type SentimentLabel,
} from "@/lib/supabase";

// ─────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────
interface DashboardState {
  stats: {
    totalMentions: number;
    positiveCount: number;
    negativeCount: number;
    neutralCount: number;
    netSentiment: number;
    localTermOverrides: number;
  } | null;
  summaries: SentimentSummary[];
  trends: DailyTrend[];
  mentions: Mention[];
  mentionsCount: number;
  selectedEntity: string;
  selectedSentiment: string;
  selectedSource: string;
  searchQuery: string;
  capexType: CapexInterpretation;
  dateRange: DateRange;
  page: number;
  loadingStats: boolean;
  loadingCharts: boolean;
  loadingMentions: boolean;
  searchingLive: boolean;
  lastUpdated: Date | null;
  dbConnected: boolean | null;   // null = checking, true/false = result
  errorStats: string | null;
  errorMentions: string | null;
  liveSearchMsg: string | null;
}

const INITIAL_STATE: DashboardState = {
  stats: null,
  summaries: [],
  trends: [],
  mentions: [],
  mentionsCount: 0,
  selectedEntity: "all",
  selectedSentiment: "all",
  selectedSource: "all",
  searchQuery: "",
  capexType: null,
  dateRange: { preset: "all" },
  page: 0,
  loadingStats: true,
  loadingCharts: true,
  loadingMentions: true,
  searchingLive: false,
  lastUpdated: null,
  dbConnected: null,
  errorStats: null,
  errorMentions: null,
  liveSearchMsg: null,
};

const MENTIONS_PER_PAGE = 12;

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const [state, setState] = useState<DashboardState>(INITIAL_STATE);
  const feedRef = useRef<HTMLDivElement>(null);

  const updateState = useCallback((updates: Partial<DashboardState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  }, []);

  // Rango de fechas resuelto
  const resolvedDates = resolveDateRange(state.dateRange);

  // ── Test de conexión a Supabase ─────────────────────────────
  useEffect(() => {
    testConnection().then(({ ok, error }) => {
      updateState({ dbConnected: ok });
      if (!ok) {
        console.warn("Supabase connection failed:", error);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Carga de stats + resúmenes ──────────────────────────────
  const loadStats = useCallback(async (dateFrom?: string, dateTo?: string, entity?: string, query?: string) => {
    try {
      updateState({ loadingStats: true, errorStats: null });
      const [stats, summaries] = await Promise.all([
        fetchTotalStats(dateFrom, dateTo, entity, query),
        fetchSentimentSummary(),
      ]);
      updateState({ stats, summaries, loadingStats: false });
    } catch (err: any) {
      const msg = err?.message ?? "Error desconocido al cargar estadísticas";
      console.error("Error cargando stats:", msg);
      updateState({ loadingStats: false, errorStats: msg });
    }
  }, [updateState]);

  // ── Carga de tendencias ─────────────────────────────────────
  const loadCharts = useCallback(async (entitySlug?: string, dateFrom?: string, dateTo?: string, query?: string) => {
    try {
      updateState({ loadingCharts: true });
      const trends = await fetchDailyTrend(
        entitySlug === "all" ? undefined : entitySlug,
        dateFrom,
        dateTo,
        query
      );
      updateState({ trends, loadingCharts: false });
    } catch (err: any) {
      console.error("Error cargando trends:", err?.message);
      updateState({ loadingCharts: false });
    }
  }, [updateState]);

  // ── Búsqueda en vivo (llamada al API route) ─────────────────
  const triggerLiveSearch = useCallback(async (query: string) => {
    if (!query || query.trim().length < 2) return;
    try {
      updateState({ searchingLive: true, liveSearchMsg: null });
      const res = await fetch("/api/search-live", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const json = await res.json();
      if (json.newMentions > 0) {
        updateState({
          liveSearchMsg: `✓ ${json.newMentions} resultado(s) nuevo(s) encontrado(s) en vivo`,
          searchingLive: false,
        });
      } else {
        updateState({
          liveSearchMsg: json.message ?? "Sin resultados nuevos en Reddit / Noticias",
          searchingLive: false,
        });
      }
    } catch {
      updateState({ searchingLive: false, liveSearchMsg: null });
    }
  }, [updateState]);

  // ── Carga de menciones ──────────────────────────────────────
  const loadMentions = useCallback(async (params: {
    entitySlug?: string;
    sentiment?: string;
    sourceSlug?: string;
    searchQuery?: string;
    dateFrom?: string;
    dateTo?: string;
    page?: number;
  }) => {
    try {
      updateState({ loadingMentions: true, errorMentions: null });
      const { entitySlug, sentiment, sourceSlug, searchQuery, dateFrom, dateTo, page = 0 } = params;

      const { data, count } = await fetchMentions({
        entitySlug: entitySlug === "all" ? undefined : entitySlug,
        sentiment: sentiment === "all" ? undefined : (sentiment as SentimentLabel),
        sourceSlug: sourceSlug === "all" ? undefined : sourceSlug,
        searchQuery,
        dateFrom,
        dateTo,
        limit: MENTIONS_PER_PAGE,
        offset: page * MENTIONS_PER_PAGE,
      });

      updateState({
        mentions: data,
        mentionsCount: count,
        loadingMentions: false,
        lastUpdated: new Date(),
      });
    } catch (err: any) {
      const msg = err?.message ?? "Error desconocido al cargar menciones";
      console.error("Error cargando menciones:", msg);
      updateState({ loadingMentions: false, errorMentions: msg });
    }
  }, [updateState]);

  // Helpers to resolve effective entity
  const resolveEffectiveFilters = useCallback(() => {
    let effectiveEntity = state.selectedEntity;
    let effectiveQuery = state.searchQuery;

    if (state.capexType === "financial") {
      updateState({ mentions: [], mentionsCount: 0, loadingMentions: false });
      return { skip: true, effectiveEntity, effectiveQuery };
    }

    return { skip: false, effectiveEntity, effectiveQuery };
  }, [state.selectedEntity, state.searchQuery, state.capexType, updateState]);

  // ── Carga inicial ───────────────────────────────────────────
  useEffect(() => {
    const { from, to } = resolveDateRange(INITIAL_STATE.dateRange);
    loadStats(from, to, undefined, undefined);
    loadCharts(undefined, from, to, undefined);
    loadMentions({ dateFrom: from, dateTo: to, page: 0 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Reload cuando cambian filtros ───────────────────────────
  useEffect(() => {
    const { from, to } = resolvedDates;
    const { skip, effectiveEntity, effectiveQuery } = resolveEffectiveFilters();

    if (!skip) {
      loadStats(from, to, effectiveEntity, effectiveQuery);
      loadCharts(effectiveEntity, from, to, effectiveQuery);
      loadMentions({
        entitySlug: effectiveEntity,
        sentiment: state.selectedSentiment,
        sourceSlug: state.selectedSource,
        searchQuery: effectiveQuery,
        dateFrom: from,
        dateTo: to,
        page: state.page,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    state.selectedEntity,
    state.selectedSentiment,
    state.selectedSource,
    state.searchQuery,
    state.capexType,
    state.dateRange,
    state.page,
  ]);

  useEffect(() => {
    const { from, to } = resolvedDates;
    const { skip, effectiveEntity, effectiveQuery } = resolveEffectiveFilters();

    if (!skip) {
      loadCharts(effectiveEntity, from, to, effectiveQuery);
      loadStats(from, to, effectiveEntity, effectiveQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.selectedEntity, state.dateRange, state.searchQuery, state.capexType]);

  // ── Handlers ────────────────────────────────────────────────
  const handleSearch = useCallback((query: string, capexType?: CapexInterpretation) => {
    let newEntity = state.selectedEntity;
    let newQuery = query;

    if (capexType === "institution") {
      newEntity = "capex-institucion";
      newQuery = ""; // Filtrar por entidad, no por texto
    }

    updateState({
      searchQuery: newQuery,
      capexType: capexType ?? null,
      page: 0,
      liveSearchMsg: null,
      selectedEntity: newEntity
    });

    // Disparar búsqueda en vivo para enriquecer la DB con resultados en tiempo real
    if (newQuery && newQuery.trim().length >= 2) {
      triggerLiveSearch(newQuery);
    }
  }, [updateState, triggerLiveSearch, state.selectedEntity]);

  const handleGenerateReport = useCallback(() => {
    const doc = new jsPDF();
    const now = new Date().toLocaleString();

    doc.setFontSize(20);
    doc.setTextColor(30, 58, 138);
    doc.text("Social Intelligence Hub - Reporte Ejecutivo", 14, 22);

    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(`Generado el: ${now}`, 14, 30);
    doc.text(`Entidad: ${state.selectedEntity === 'all' ? 'Todas las entidades' : state.selectedEntity}`, 14, 35);

    if (state.stats) {
      doc.setFontSize(14);
      doc.setTextColor(0);
      doc.text("Resumen de Metricas", 14, 50);

      autoTable(doc, {
        startY: 55,
        head: [['KPI', 'Valor']],
        body: [
          ['Menciones Totales', state.stats.totalMentions.toString()],
          ['Sentimiento Neto', `${state.stats.netSentiment}%`],
          ['Menciones Positivas', state.stats.positiveCount.toString()],
          ['Menciones Negativas', state.stats.negativeCount.toString()],
          ['Menciones Neutras', state.stats.neutralCount.toString()],
          ['Correcciones Locales', state.stats.localTermOverrides.toString()],
        ],
        theme: 'striped',
        headStyles: { fillColor: [30, 58, 138] }
      });
    }

    const topMentions = state.mentions.slice(0, 5);
    if (topMentions.length > 0) {
      doc.setFontSize(14);
      doc.text("Menciones Recientes mas Relevantes", 14, (doc as any).lastAutoTable.finalY + 15);

      autoTable(doc, {
        startY: (doc as any).lastAutoTable.finalY + 20,
        head: [['Fecha', 'Fuente', 'Autor', 'Sentimiento', 'Texto']],
        body: topMentions.map(m => [
          m.published_at ? m.published_at.substring(0, 10) : '-',
          m.sources?.name || 'Web',
          m.author_name || 'Anonimo',
          m.sentiment_label,
          m.text_original.substring(0, 80) + '...'
        ]),
        columnStyles: {
          4: { cellWidth: 80 }
        },
        theme: 'grid',
        headStyles: { fillColor: [15, 23, 42] }
      });
    }

    doc.save(`reporte-social-intelligence-${state.selectedEntity}-${new Date().getTime()}.pdf`);
  }, [state.stats, state.selectedEntity, state.mentions]);

  const handleEntityChange = useCallback((entity: string) => {
    updateState({ selectedEntity: entity, page: 0 });
  }, [updateState]);

  // Clic en KPI → filtra el feed y hace scroll a él
  const handleKpiClick = useCallback((sentiment: string) => {
    const next = state.selectedSentiment === sentiment ? "all" : sentiment;
    updateState({ selectedSentiment: next, page: 0 });
    setTimeout(() => feedRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
  }, [state.selectedSentiment, updateState]);

  const handleSentimentChange = useCallback((sentiment: string) => {
    updateState({ selectedSentiment: sentiment, page: 0 });
  }, [updateState]);

  const handleDateRangeChange = useCallback((range: DateRange) => {
    updateState({ dateRange: range, page: 0 });
  }, [updateState]);

  const handleRefresh = useCallback(() => {
    const { from, to } = resolvedDates;
    updateState({ liveSearchMsg: null });
    loadStats(from, to);
    loadCharts(state.selectedEntity, from, to);
    loadMentions({
      entitySlug: state.selectedEntity,
      sentiment: state.selectedSentiment,
      sourceSlug: state.selectedSource,
      searchQuery: state.searchQuery,
      capexType: state.capexType,
      dateFrom: from,
      dateTo: to,
      page: 0,
    });
    updateState({ page: 0 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  // ── Datos derivados ─────────────────────────────────────────
  const selectedSummary =
    state.summaries.find((s) => s.entity_slug === state.selectedEntity)
    ?? state.summaries[0]
    ?? null;

  const entityFilterOptions = [
    { value: "all", label: "Todas las entidades" },
    ...state.summaries.map((s) => ({
      value: s.entity_slug,
      label: s.entity_name,
      count: s.total_mentions,
    })),
  ];

  const sentimentFilterOptions = [
    { value: "all", label: "Todos" },
    { value: "positive", label: "Positivos" },
    { value: "negative", label: "Negativos" },
    { value: "neutral", label: "Neutros" },
    { value: "mixed", label: "Mixtos" },
  ];

  const totalPages = Math.ceil(state.mentionsCount / MENTIONS_PER_PAGE);
  const positivePct = state.stats && state.stats.totalMentions > 0
    ? Math.round((state.stats.positiveCount / state.stats.totalMentions) * 100) : 0;
  const negativePct = state.stats && state.stats.totalMentions > 0
    ? Math.round((state.stats.negativeCount / state.stats.totalMentions) * 100) : 0;

  // ── Render ──────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-background">

      {/* ────── HEADER ────── */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between sm:gap-4 gap-3">

          {/* Brand */}
          <div className="flex items-center gap-2.5 flex-shrink-0 order-1">
            <div className="p-1.5 rounded-lg bg-czfs-blue">
              <BarChart2 className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-sm font-bold text-czfs-navy leading-tight">
                Social Intelligence Hub
              </p>
              <p className="text-[10px] text-muted-foreground leading-tight">
                CZFS &amp; CAPEX
              </p>
            </div>
          </div>

          {/* Search */}
          <div className="flex-1 min-w-[280px] w-full sm:max-w-xl order-3 sm:order-2 header-search">
            <SearchBar
              onSearch={handleSearch}
              loading={state.loadingMentions || state.searchingLive}
              initialValue={state.searchQuery}
            />
          </div>

          {/* Acciones */}
          <div className="flex items-center gap-2 flex-shrink-0 order-2 sm:order-3">
            {state.lastUpdated && (
              <span className="text-xs text-muted-foreground hidden md:block">
                Act. {formatShortDate(state.lastUpdated.toISOString())}
              </span>
            )}
            <button
              onClick={handleGenerateReport}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
              title="Descargar reporte PDF"
              disabled={!state.stats}
            >
              <FileText className="h-4 w-4 text-muted-foreground" />
            </button>
            <button
              onClick={handleRefresh}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
              title="Actualizar datos"
            >
              <RefreshCw className={cn("h-4 w-4 text-muted-foreground",
                (state.loadingStats || state.loadingMentions) && "animate-spin"
              )} />
            </button>
            <button className="p-2 rounded-lg hover:bg-muted transition-colors relative">
              <Bell className="h-4 w-4 text-muted-foreground" />
              {negativePct > 30 && (
                <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 bg-red-500 rounded-full animate-pulse" />
              )}
            </button>
          </div>
        </div>
      </header>

      {/* ────── BANNER ESTADO DB ────── */}
      {state.dbConnected === false && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-2.5">
          <div className="max-w-7xl mx-auto flex items-center gap-2 text-sm text-red-700">
            <WifiOff className="h-4 w-4 flex-shrink-0" />
            <strong>Sin conexión a Supabase.</strong>
            <span>Verifica tu <code className="bg-red-100 px-1 rounded">.env.local</code> y que el SQL de migración haya sido ejecutado.</span>
          </div>
        </div>
      )}

      {/* ────── BANNER ERROR STATS ────── */}
      {state.errorStats && state.dbConnected !== false && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2.5">
          <div className="max-w-7xl mx-auto flex items-center gap-2 text-sm text-amber-700">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            <span>Las tablas o vistas aún no existen en Supabase. Ejecuta el SQL de migración primero.</span>
            <span className="text-xs ml-2 text-amber-500">{state.errorStats}</span>
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-7">

        {/* ────── FILTRO DE PERÍODO ────── */}
        <section className="bg-card border rounded-xl px-5 py-3.5 shadow-sm">
          <DateRangeFilter
            value={state.dateRange}
            onChange={handleDateRangeChange}
          />
        </section>

        {/* ────── KPIs ────── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Salud de la Marca
            </h2>
            <p className="text-xs text-muted-foreground">
              Los indicadores son interactivos — haz clic para filtrar el feed
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">

            {/* Gauge Sentimiento Neto */}
            <div className="col-span-2 md:col-span-1">
              <NetSentimentCard
                score={state.stats?.netSentiment ?? 0}
                totalMentions={state.stats?.totalMentions ?? 0}
                loading={state.loadingStats}
                onClick={() => handleKpiClick("all")}
                active={state.selectedSentiment === "all"}
              />
            </div>

            <KpiCard
              title="Total Menciones"
              value={formatNumber(state.stats?.totalMentions ?? 0)}
              subtitle="en el período"
              icon={<Globe className="h-4 w-4" />}
              accentColor="#1E3A8A"
              loading={state.loadingStats}
              active={state.selectedSentiment === "all"}
              onClick={() => handleKpiClick("all")}
            />

            <KpiCard
              title="Menciones Positivas"
              value={formatNumber(state.stats?.positiveCount ?? 0)}
              subtitle={`${positivePct}% del total`}
              icon={<ThumbsUp className="h-4 w-4" />}
              accentColor="#059669"
              loading={state.loadingStats}
              active={state.selectedSentiment === "positive"}
              onClick={() => handleKpiClick("positive")}
            />

            <KpiCard
              title="Menciones Negativas"
              value={formatNumber(state.stats?.negativeCount ?? 0)}
              subtitle={`${negativePct}% del total`}
              icon={<ThumbsDown className="h-4 w-4" />}
              accentColor="#DC2626"
              loading={state.loadingStats}
              active={state.selectedSentiment === "negative"}
              onClick={() => handleKpiClick("negative")}
            />

            <KpiCard
              title="Neutras"
              value={formatNumber(state.stats?.neutralCount ?? 0)}
              subtitle="sin polaridad definida"
              icon={<Minus className="h-4 w-4" />}
              accentColor="#4B5563"
              loading={state.loadingStats}
              active={state.selectedSentiment === "neutral"}
              onClick={() => handleKpiClick("neutral")}
            />
          </div>
        </section>

        {/* ────── GRÁFICOS ────── */}
        <section>
          <div className="flex items-center justify-between mb-4 flex-wrap gap-4">
            <h2 className="text-[11px] font-bold uppercase tracking-[0.15em] text-slate-400">
              Análisis de Tendencias
            </h2>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Contexto:</span>
                <select
                  value={state.selectedEntity}
                  onChange={(e) => handleEntityChange(e.target.value)}
                  className="text-xs font-bold border-slate-200 border rounded-lg px-3 py-1.5 bg-white text-czfs-navy
                             focus:outline-none focus:ring-2 focus:ring-czfs-blue/20 transition-all cursor-pointer shadow-sm"
                >
                  {entityFilterOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              {state.selectedEntity !== "all" && (
                <Link
                  href={`/entidad/${state.selectedEntity}`}
                  className="text-[10px] font-bold text-czfs-blue hover:text-czfs-blue/80 flex items-center gap-1.5 bg-blue-50/50 px-3 py-1.5 rounded-lg border border-blue-100/50 transition-all hover:shadow-sm"
                >
                  <BarChart3 className="h-3 w-3" />
                  VER PERFIL COMPLETO
                  <ArrowUpRight className="h-3 w-3" />
                </Link>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <TrendChart
                data={state.trends}
                loading={state.loadingCharts}
                entitySlug={state.selectedEntity === "all" ? undefined : state.selectedEntity}
                onBarClick={(sentiment) => handleKpiClick(sentiment)}
              />
            </div>
            <SentimentDonut
              summary={selectedSummary}
              loading={state.loadingStats}
              onSliceClick={(sentiment) => handleKpiClick(sentiment)}
            />
          </div>

          {state.summaries.length > 1 && (
            <div className="mt-4">
              <EntitiesComparisonChart
                summaries={state.summaries}
                loading={state.loadingStats}
                onEntityClick={(slug) => handleEntityChange(slug)}
              />
            </div>
          )}
        </section>

        {/* ────── FEED ────── */}
        <section ref={feedRef}>
          <div className="flex items-start justify-between mb-3 flex-wrap gap-3">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Feed de Menciones
              </h2>
              {!state.loadingMentions && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  {state.mentionsCount.toLocaleString()} resultado{state.mentionsCount !== 1 ? "s" : ""}
                  {state.selectedSentiment !== "all" && ` · ${state.selectedSentiment}`}
                  {state.searchQuery && ` · "${state.searchQuery}"`}
                </p>
              )}
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <Filter className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
              <FilterChips
                options={sentimentFilterOptions}
                selected={state.selectedSentiment}
                onChange={handleSentimentChange}
              />
            </div>
          </div>

          {/* Aviso búsqueda en vivo */}
          {state.searchingLive && (
            <div className="mb-4 p-3 rounded-xl border border-blue-200 bg-blue-50 flex items-center gap-2 text-sm text-blue-700">
              <Zap className="h-4 w-4 animate-pulse flex-shrink-0" />
              Buscando en Reddit y Google News en tiempo real…
            </div>
          )}
          {state.liveSearchMsg && !state.searchingLive && (
            <div className="mb-4 p-3 rounded-xl border border-green-200 bg-green-50 flex items-center gap-2 text-sm text-green-700">
              <Zap className="h-4 w-4 flex-shrink-0" />
              {state.liveSearchMsg}
            </div>
          )}

          {/* Aviso CAPEX financiero */}
          {state.capexType === "financial" && (
            <div className="mb-4 p-4 rounded-xl border border-amber-200 bg-amber-50 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-amber-800">
                  CAPEX financiero está fuera del ámbito de monitoreo
                </p>
                <p className="text-xs text-amber-700 mt-0.5">
                  Este hub monitorea CZFS y CAPEX como institución educativa.
                  Para Capital Expenditure, usa herramientas financieras especializadas.
                </p>
              </div>
            </div>
          )}

          {/* Error mentions */}
          {state.errorMentions && !state.loadingMentions && (
            <div className="mb-4 p-4 rounded-xl border border-red-200 bg-red-50 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-red-700">Error cargando menciones</p>
                <p className="text-xs text-red-600 mt-0.5">{state.errorMentions}</p>
                <p className="text-xs text-red-500 mt-1">
                  Verifica que el SQL de migración fue ejecutado en Supabase → SQL Editor.
                </p>
              </div>
            </div>
          )}

          {/* Grid de menciones */}
          {console.log("Mentions in render:", state.mentions)}
          {state.loadingMentions ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 gap-4 max-w-7xl mx-auto">
              {Array.from({ length: 6 }).map((_, i) => <MentionCardSkeleton key={i} />)}
            </div>
          ) : state.mentions.length === 0 && !state.errorMentions ? (
            <div className="text-center py-16 border-2 border-dashed rounded-xl bg-card">
              <p className="text-sm font-medium text-foreground">Sin menciones para los filtros seleccionados</p>
              <p className="text-xs text-muted-foreground mt-1">
                {state.dbConnected === false
                  ? "La base de datos no está conectada. Revisa tus credenciales en .env.local"
                  : "Prueba cambiando el período, la entidad o los filtros de sentimiento."}
              </p>
              {state.dbConnected !== false && (
                <p className="text-xs text-muted-foreground mt-1">
                  Si es la primera vez, ejecuta el SQL de migración en Supabase para insertar datos demo.
                </p>
              )}
            </div>
          ) : !state.errorMentions ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 gap-4 max-w-7xl mx-auto">
              {state.mentions.map((mention) => (
                <MentionCard key={mention.id} mention={mention} />
              ))}
            </div>
          ) : null}

          {/* Paginación */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 mt-6">
              <button
                onClick={() => updateState({ page: Math.max(0, state.page - 1) })}
                disabled={state.page === 0}
                className="px-4 py-2 text-xs font-medium rounded-lg border hover:bg-muted
                           disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Anterior
              </button>
              <span className="text-xs text-muted-foreground tabular-nums">
                Página {state.page + 1} de {totalPages}
              </span>
              <button
                onClick={() => updateState({ page: Math.min(totalPages - 1, state.page + 1) })}
                disabled={state.page >= totalPages - 1}
                className="px-4 py-2 text-xs font-medium rounded-lg border hover:bg-muted
                           disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Siguiente
              </button>
            </div>
          )}
        </section>

        {/* ────── FOOTER ────── */}
        <footer className="border-t pt-5 pb-3">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-czfs-blue">CZFS</span>
              <span>·</span>
              <span>Social Intelligence Hub</span>
              <span>·</span>
              <span>v0.1.0</span>
            </div>
            <div className="flex items-center gap-4">
              {/* Indicador de conexión real */}
              <span className="flex items-center gap-1">
                {state.dbConnected === null && (
                  <span className="h-2 w-2 rounded-full bg-yellow-400 inline-block animate-pulse" />
                )}
                {state.dbConnected === true && (
                  <span className="h-2 w-2 rounded-full bg-green-500 inline-block" />
                )}
                {state.dbConnected === false && (
                  <span className="h-2 w-2 rounded-full bg-red-500 inline-block" />
                )}
                {state.dbConnected === null ? "Conectando…" :
                  state.dbConnected ? "Supabase conectado" : "Supabase desconectado"}
              </span>
              <span>Búsqueda en vivo: Reddit · Google News</span>
              <span className="hidden sm:inline">Stack: Next.js 15 · Tailwind · Recharts</span>
            </div>
          </div>
        </footer>

      </main>
    </div>
  );
}
