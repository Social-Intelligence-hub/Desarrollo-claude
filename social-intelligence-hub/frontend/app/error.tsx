"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

// Error boundary global del App Router.
// Captura errores no manejados de los Server/Client Components hijos.
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Telemetría — por ahora solo a la consola.
    // Cuando se agregue Sentry/Logflare/etc., enviar `error` aquí.
    console.error("[GlobalError]", error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-slate-50">
      <div className="max-w-md w-full bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center">
        <div className="mx-auto w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mb-4">
          <AlertTriangle className="w-6 h-6 text-red-600" />
        </div>
        <h1 className="text-xl font-semibold text-slate-900 mb-2">
          Algo salió mal
        </h1>
        <p className="text-sm text-slate-600 mb-6">
          Ocurrió un error inesperado al cargar el dashboard.{" "}
          {error.digest && (
            <span className="block mt-2 text-xs text-slate-400">
              Ref: {error.digest}
            </span>
          )}
        </p>
        <button
          onClick={reset}
          className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Reintentar
        </button>
      </div>
    </div>
  );
}
