"use client";

import { useState, useEffect, useCallback, use } from "react";
import Link from "next/link";
import {
  ChevronLeft, Globe, ThumbsUp, ThumbsDown, Minus,
  TrendingUp, BarChart3, MessageSquare, Calendar
} from "lucide-react";
import {
  fetchEntityBySlug,
  fetchTotalStats,
  fetchDailyTrend,
  fetchMentions,
  fetchSourceStats,
  type Entity,
  type Mention,
  type DailyTrend
} from "@/lib/supabase";
import { KpiCard, NetSentimentCard } from "@/components/KpiCard";
import { TrendChart } from "@/components/SentimentChart";
import { MentionCard } from "@/components/MentionCard";
import { formatNumber } from "@/lib/utils";

interface EntityPageProps {
  params: Promise<{ slug: string }>;
}

export default function EntityDetailPage({ params }: EntityPageProps) {
  const { slug } = use(params);

  const [entity, setEntity] = useState<Entity | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [trends, setTrends] = useState<DailyTrend[]>([]);
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [sourceStats, setSourceStats] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [e, s, t, m, ss] = await Promise.all([
        fetchEntityBySlug(slug),
        fetchTotalStats(undefined, undefined, slug),
        fetchDailyTrend(slug),
        fetchMentions({ entitySlug: slug, limit: 10 }),
        fetchSourceStats(slug)
      ]);

      setEntity(e);
      setStats(s);
      setTrends(t);
      setMentions(m.data);
      setSourceStats(ss);
    } catch (err) {
      console.error("Error loading entity details:", err);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 border-4 border-czfs-blue border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-medium text-slate-500">Cargando perfil de entidad...</p>
        </div>
      </div>
    );
  }

  if (!entity) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center p-8 bg-white rounded-2xl shadow-xl border border-slate-200">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Entidad no encontrada</h1>
          <p className="text-slate-500 mb-6">No pudimos encontrar información para "{slug}"</p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-6 py-3 bg-czfs-blue text-white rounded-xl font-semibold hover:bg-czfs-blue/90 transition-all shadow-md hover:shadow-lg active:scale-95"
          >
            <ChevronLeft className="h-4 w-4" />
            Volver al Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC]">

      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors text-slate-500"
              title="Volver"
            >
              <ChevronLeft className="h-5 w-5" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900">{entity.name}</h1>
                <span className="px-2 py-0.5 bg-slate-100 text-slate-500 text-[10px] font-bold uppercase tracking-wider rounded-md border border-slate-200">
                  {entity.category}
                </span>
              </div>
              <p className="text-xs text-slate-500">Análisis detallado de reputación y menciones</p>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-4">
            <div className="text-right">
              <p className="text-[10px] font-bold text-slate-400 uppercase">Estado</p>
              <div className="flex items-center gap-1.5 justify-end">
                <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-xs font-semibold text-slate-700 uppercase tracking-tighter">Monitoreo Activo</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">


        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <NetSentimentCard
            score={stats?.netSentiment ?? 0}
            totalMentions={stats?.totalMentions ?? 0}
          />

          <KpiCard
            title="Alcance Total"
            value={formatNumber(stats?.totalMentions ?? 0)}
            subtitle="menciones detectadas"
            icon={<Globe className="h-4 w-4" />}
            accentColor="#1E3A8A"
          />

          <KpiCard
            title="Impacto Positivo"
            value={formatNumber(stats?.positiveCount ?? 0)}
            subtitle={`${stats?.totalMentions > 0 ? Math.round((stats.positiveCount / stats.totalMentions) * 100) : 0}% del volumen`}
            icon={<ThumbsUp className="h-4 w-4" />}
            accentColor="#059669"
          />

          <KpiCard
            title="Riesgo / Negativo"
            value={formatNumber(stats?.negativeCount ?? 0)}
            subtitle="requiere atención"
            icon={<ThumbsDown className="h-4 w-4" />}
            accentColor="#DC2626"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">


          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-czfs-blue" />
                  <h2 className="text-lg font-bold text-slate-900">Evolución Temporal</h2>
                </div>
              </div>
              <TrendChart
                data={trends}
                entitySlug={slug}
              />
            </div>


            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-czfs-blue" />
                  <h2 className="text-lg font-bold text-slate-900">Últimas Interacciones</h2>
                </div>
                <span className="text-xs text-slate-500 font-medium bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
                  Mostrando las últimas 10
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {mentions.map((m) => (
                  <MentionCard key={m.id} mention={m} compact />
                ))}
              </div>

              {mentions.length === 0 && (
                <div className="bg-white border-2 border-dashed border-slate-200 rounded-2xl py-16 text-center">
                  <p className="text-slate-400 font-medium">No hay menciones recientes para esta entidad.</p>
                </div>
              )}
            </div>
          </div>


          <div className="space-y-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center gap-2 mb-6 text-slate-900">
                <BarChart3 className="h-5 w-5 text-czfs-blue" />
                <h2 className="text-lg font-bold">Distribución por Fuente</h2>
              </div>
              <div className="space-y-4">
                {sourceStats.map((source, i) => (
                  <div key={i} className="space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-semibold text-slate-700">{source.source_name}</span>
                      <span className="text-slate-500 font-mono text-xs">{source.count}</span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-czfs-blue rounded-full"
                        style={{ width: `${(source.count / (stats?.totalMentions || 1)) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
                {sourceStats.length === 0 && (
                  <p className="text-center text-xs text-slate-400 py-4">Sin datos de fuentes</p>
                )}
              </div>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center gap-2 mb-4 text-slate-900">
                <Globe className="h-5 w-5 text-czfs-blue" />
                <h2 className="text-lg font-bold">Palabras Clave</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {entity.keywords.map((kw, i) => (
                  <span key={i} className="px-2.5 py-1 bg-blue-50 text-czfs-blue text-[11px] font-bold rounded-lg border border-blue-100">
                    {kw}
                  </span>
                ))}
              </div>
              {entity.description && (
                <div className="mt-6 pt-6 border-t border-slate-100 text-xs text-slate-500 leading-relaxed italic">
                  "{entity.description}"
                </div>
              )}
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
