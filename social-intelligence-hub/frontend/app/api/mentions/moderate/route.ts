import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const validKey = (serviceKey && serviceKey !== "PENDING") ? serviceKey : process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  validKey
);

/**
 * POST /api/mentions/feedback
 * Elimina una mención irrelevante de la base de datos y añade feedback.
 */
export async function POST(request: NextRequest) {
  try {
    const { id, reason } = await request.json();

    if (!id) {
      return NextResponse.json({ error: "Falta el ID de la mención" }, { status: 400 });
    }

    // 1. Obtener los detalles de la mención antes de borrarla
    const { data: mention, error: selectError } = await supabase
      .from("mentions")
      .select("text_original")
      .eq("id", id)
      .single();
      
    if (selectError) {
        console.error("Error fetching mention:", selectError);
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
        console.warn("No se pudo guardar feedback (puede que falte crear la tabla):", insertError);
      }
    }

    // 3. Borrar la mención
    const { error } = await supabase
      .from("mentions")
      .delete()
      .eq("id", id);

    if (error) throw error;

    return NextResponse.json({ success: true });
  } catch (err: any) {
    console.error("Error rechazando mención:", err.message);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
