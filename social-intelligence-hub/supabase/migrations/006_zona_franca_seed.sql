-- ============================================================
-- 006_zona_franca_seed.sql
-- Conglomerado "zona-franca" + 35 entidades reales (afiliadas AEZFC /
-- ecosistema CZFS) + entity_configs baseline.
-- Fuente de la lista: aezfc.org/directorio-de-afiliados + zonafrancasantiago.com
-- + nombres representativos de PROYECTO.md. Idempotente (ON CONFLICT).
-- Las queries baseline se pueden ENRIQUECER luego con setup/discover_entities.py (Gemini).
-- ============================================================

-- 1) Conglomerado
INSERT INTO conglomerates (slug, name, category, website, context_description, primary_geo)
VALUES (
  'zona-franca',
  'Corporación Zona Franca Santiago',
  'zona-franca',
  'https://www.zonafrancasantiago.com',
  'Conglomerado industrial (zona franca) del norte de República Dominicana, con ~35 empresas afiliadas en los parques PIVEM (Víctor Espaillat Mera), Tamboril y Caribbean Industrial Park (CIP/Matanza), en Santiago de los Caballeros. Sectores: tabaco/cigarros, textil y confección, calzado y cuero, electrónica, empaque, logística y servicios. Contexto de desambiguación: cualquier mención se interpreta en clave dominicana (Santiago RD, no Santiago de Chile). "CAPEX" en este ecosistema es el centro de capacitación formativa de la corporación, NO el término financiero (capital expenditure).',
  'Santiago, RD'
)
ON CONFLICT (slug) DO UPDATE
  SET name = EXCLUDED.name,
      website = EXCLUDED.website,
      context_description = EXCLUDED.context_description,
      primary_geo = EXCLUDED.primary_geo;

-- 2) Entidades (35). priority=TRUE en 15 (mayor perfil de prensa/empleo).
WITH cg AS (SELECT id FROM conglomerates WHERE slug = 'zona-franca')
INSERT INTO entities (slug, name, category, conglomerate_id, priority, keywords, description)
SELECT v.slug, v.name, v.category, cg.id, v.priority, v.keywords, v.descr
FROM cg, (VALUES
  ('la-aurora','La Aurora','tabaco',TRUE, ARRAY['la aurora','tabacalera la aurora','aurora cigars'], 'Tabacalera La Aurora — la fábrica de cigarros más antigua de RD.'),
  ('arturo-fuente','Arturo Fuente','tabaco',TRUE, ARRAY['arturo fuente','fuente cigars','tabacalera fuente'], 'Tabacalera Arturo Fuente — cigarros premium.'),
  ('general-cigar','General Cigar Dominicana','tabaco',TRUE, ARRAY['general cigar','general cigar dominicana'], 'Productora de cigarros (Macanudo, Partagas DR).'),
  ('swedish-match','Swedish Match','tabaco',TRUE, ARRAY['swedish match'], 'Manufactura de tabaco/fósforos.'),
  ('swisher-dominicana','Swisher Dominicana','tabaco',TRUE, ARRAY['swisher','swisher dominicana'], 'Swisher Dominicana Inc. — cigarros y tabaco.'),
  ('quesada-cigars','Quesada Cigars','tabaco',TRUE, ARRAY['quesada cigars','quesada','matasa'], 'Quesada Cigars / MATASA — cigarros.'),
  ('procigar','ProCigar','gremio-tabaco',TRUE, ARRAY['procigar','pro cigar','festival procigar'], 'Asociación de fabricantes de cigarros (Festival ProCigar).'),
  ('grupo-m','Grupo M','textil',TRUE, ARRAY['grupo m','codevi'], 'Grupo M — manufactura textil y confección.'),
  ('hanesbrands','Hanesbrands','textil',TRUE, ARRAY['hanesbrands','hanes'], 'Hanesbrands — confección de ropa.'),
  ('keen-footwear','Keen Footwear','calzado',TRUE, ARRAY['keen','keen footwear'], 'Keen — calzado outdoor.'),
  ('eaton-souriau','Eaton Souriau','electronica',TRUE, ARRAY['eaton souriau','eaton','souriau'], 'Eaton Souriau — conectores electrónicos.'),
  ('iem-corporation','IEM Corporation','electronica',TRUE, ARRAY['iem corporation','iem'], 'IEM Corporation — manufactura electrónica/médica.'),
  ('empa','EMPA','manufactura',TRUE, ARRAY['empa'], 'EMPA — manufactura.'),
  ('pivem','PIVEM','parque',TRUE, ARRAY['pivem','parque industrial victor espaillat','villa europa'], 'Parque Industrial Víctor Espaillat Mera — principal parque de CZFS.'),
  ('capex','CAPEX','educacion',TRUE, ARRAY['capex','centro de capacitacion','capacitacion zona franca'], 'CAPEX — centro de capacitación y formación de CZFS (NO el término financiero).'),
  ('elevate-textiles','Elevate Textiles','textil',FALSE, ARRAY['elevate textiles','ae create'], 'AE Create / Elevate Textiles — textil.'),
  ('star-sew','Star Sew','textil',FALSE, ARRAY['star sew','smc'], 'Star Sew (SMC) — confección.'),
  ('varsity-spirit','Varsity Spirit','apparel',FALSE, ARRAY['varsity spirit'], 'Varsity Spirit — uniformes/apparel.'),
  ('batu-wear','Batú Wear','apparel',FALSE, ARRAY['batu wear','batú wear'], 'Batú Wear — apparel.'),
  ('sky-sands-footwear','Sky Sands Footwear','calzado',FALSE, ARRAY['sky sands','sky sands footwear'], 'Sky Sands — calzado.'),
  ('bojos-tanning','Bojos Tanning','cuero',FALSE, ARRAY['bojos tanning','bojs tanning'], 'Bojos Tanning — curtido de cuero.'),
  ('pieles-los-favoritos','Pieles Los Favoritos','cuero',FALSE, ARRAY['pieles los favoritos','los favoritos'], 'Artículos de Pieles Los Favoritos — cuero.'),
  ('mafri-electric','Mafri Electric','electrico',FALSE, ARRAY['mafri electric','mafri'], 'Mafri Electric — productos eléctricos.'),
  ('synergies-corp','Synergies Corp','manufactura',FALSE, ARRAY['synergies corp','synergies'], 'Synergies Corp — manufactura.'),
  ('ipack','iPack','empaque',FALSE, ARRAY['ipack'], 'iPack — empaque.'),
  ('pacific-packaging','Pacific Packaging','empaque',FALSE, ARRAY['pacific packaging'], 'Pacific Packaging — empaque.'),
  ('full-packing-caribe','Full Packing del Caribe','empaque',FALSE, ARRAY['full packing del caribe','full packing'], 'Full Packing del Caribe — empaque.'),
  ('zanwill-box','Zanwill Box Factory','empaque',FALSE, ARRAY['zanwill','zanwill box'], 'Zanwill Box Factory — cajas/empaque.'),
  ('king-ocean','King Ocean Services','logistica',FALSE, ARRAY['king ocean','king ocean services'], 'King Ocean Services — logística marítima.'),
  ('swen-products','Swen Products','manufactura',FALSE, ARRAY['swen products','swen'], 'Swen Products — manufactura.'),
  ('farma-extra','Farma Extra','farmaceutico',FALSE, ARRAY['farma extra'], 'Farma Extra — farmacéutico.'),
  ('cigar-rings','Cigar Rings','accesorios-tabaco',FALSE, ARRAY['cigar rings'], 'Cigar Rings — anillas/accesorios de cigarros.'),
  ('caribbean-industrial-park','Caribbean Industrial Park','parque',FALSE, ARRAY['caribbean industrial park','cip','parque matanza'], 'Caribbean Industrial Park (CIP/Matanza) — parque industrial.'),
  ('tamboril-zona-franca','Tamboril Zona Franca','parque',FALSE, ARRAY['tamboril zona franca','tamboril'], 'Parque de zona franca de Tamboril.'),
  ('medica-czfs','MÉDICA CZFS','salud',FALSE, ARRAY['medica czfs','médica czfs','centro medico zona franca'], 'Centro médico del ecosistema CZFS.')
) AS v(slug,name,category,priority,keywords,descr)
ON CONFLICT (slug) DO UPDATE
  SET conglomerate_id = EXCLUDED.conglomerate_id,
      name = EXCLUDED.name,
      category = EXCLUDED.category,
      priority = EXCLUDED.priority,
      keywords = EXCLUDED.keywords,
      description = EXCLUDED.description;

-- 3) entity_configs baseline para las 35 (uniforme + CAPEX especial).
INSERT INTO entity_configs (
  entity_id, search_queries, required_terms, forbidden_terms,
  forbidden_domains, geo_requirement, disambiguation, queries_generated_at
)
SELECT
  e.id,
  ARRAY[
    e.name || ' Zona Franca Santiago',
    e.name || ' Santiago República Dominicana',
    e.name || ' Zona Franca'
  ],
  e.keywords,
  CASE WHEN e.slug = 'capex'
    THEN ARRAY['capital expenditure','gasto de capital','inversión de capital','capex ratio','depreciación']
    ELSE ARRAY[]::TEXT[]
  END,
  ARRAY['.cl'],
  'santiago_rd',
  CASE WHEN e.slug = 'capex'
    THEN '{"positive_signals":["capacitación","formación","curso","taller","egresados","técnico","instructor","zona franca","santiago"],"negative_signals":["capital expenditure","gasto de capital","capex ratio","balance general","depreciación","chile"]}'::jsonb
    ELSE '{"positive_signals":["santiago","república dominicana","zona franca","cibao","tamboril"],"negative_signals":["chile","santiago de chile","santo domingo"]}'::jsonb
  END,
  NOW()
FROM entities e
JOIN conglomerates c ON c.id = e.conglomerate_id AND c.slug = 'zona-franca'
ON CONFLICT (entity_id) DO UPDATE
  SET search_queries = EXCLUDED.search_queries,
      required_terms = EXCLUDED.required_terms,
      forbidden_terms = EXCLUDED.forbidden_terms,
      forbidden_domains = EXCLUDED.forbidden_domains,
      geo_requirement = EXCLUDED.geo_requirement,
      disambiguation = EXCLUDED.disambiguation,
      queries_generated_at = NOW();
