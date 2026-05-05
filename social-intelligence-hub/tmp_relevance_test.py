from collectors.relevance_filter import es_relevante_dominicana

examples = [
    (
        'Chile example',
        'Los arriendos en Santiago de Chile junto a Audax Italiano muestran el ruido de comunas como Las Condes y Providencia'
    ),
    (
        'Good RD example',
        'La Corporación Zona Franca Santiago (CZFS) en Santiago de los Caballeros registra una queja sobre CAPEX y solicita respuesta administrativa.'
    ),
    (
        'Ambiguous example',
        'Santiago y zona franca aparecen en una conversación sobre exportaciones, pero sin más contexto dominicano'
    ),
    (
        'Good RD .do example',
        'Un artículo de https://elnacional.com.do informa que CZFS y CAPEX en Santiago de los Caballeros inician un proceso de queja institucional.'
    ),
    (
        'Chile domain example',
        'Una nota publicada en https://www.latercera.cl habla de la zona franca y Santiago de Chile.'
    ),
]

for label, text in examples:
    print(f'{label}: {es_relevante_dominicana(text)}')
