import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from .profiles import SourceLanguage
from .languages import get_language_data


class TranslationConfidence(str, Enum):
    EXACT = "exact"
    COMPOSED = "composed"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EasyTranslation:
    text: str
    confidence: TranslationConfidence
    translated_parts: int = 0
    total_parts: int = 0


# Canonical concept -> English, Italian, Spanish.
# Vocabulary data is UTF-8 and normalized to Unicode NFC.
_EASY_ROWS = """
user|utente|usuario
name|nome|nombre
first|primo|primero
last|ultimo|ultimo
full|completo|completo
value|valore|valor
result|risultato|resultado
count|conteggio|conteo
index|indice|indice
size|dimensione|tamaño
length|lunghezza|longitud
width|larghezza|ancho
height|altezza|alto
depth|profondita|profundidad
position|posizione|posición
location|posizione|ubicacion
path|percorso|ruta
file|file|archivo
folder|cartella|carpeta
directory|directory|directorio
source|sorgente|fuente
target|destinazione|destino
input|ingresso|entrada
output|uscita|salida
error|errore|error
warning|avviso|aviso
message|messaggio|mensaje
status|stato|estado
success|successo|exito
failure|fallimento|fallo
valid|valido|valido
invalid|non_valido|invalido
ready|pronto|listo
active|attivo|activo
enabled|abilitato|habilitado
disabled|disabilitato|deshabilitado
current|corrente|actual
previous|precedente|anterior
next|successivo|siguiente
new|nuovo|nuevo
old|vecchio|viejo
default|predefinito|predeterminado
minimum|minimo|minimo
maximum|massimo|maximo
total|totale|total
average|media|promedio
start|inizio|inicio
end|fine|fin
begin|inizia|comenzar
stop|ferma|detener
open|apri|abrir
close|chiudi|cerrar
read|leggi|leer
write|scrivi|escribir
load|carica|cargar
save|salva|guardar
create|crea|crear
delete|elimina|eliminar
remove|rimuovi|quitar
add|aggiungi|agregar
insert|inserisci|insertar
append|accoda|anexar
update|aggiorna|actualizar
change|cambia|cambiar
replace|sostituisci|reemplazar
find|trova|buscar
search|cerca|buscar
check|controlla|comprobar
validate|valida|validar
convert|converti|convertir
parse|analizza|analizar
format|formato|formato
build|costruisci|construir
compile|compila|compilar
run|esegui|ejecutar
execute|esegui|ejecutar
test|test|prueba
print|stampa|imprimir
show|mostra|mostrar
hide|nascondi|ocultar
get|ottieni|obtener
set|imposta|establecer
reset|reimposta|restablecer
clear|pulisci|limpiar
copy|copia|copiar
move|sposta|mover
select|seleziona|seleccionar
compare|confronta|comparar
calculate|calcola|calcular
compute|calcola|calcular
process|elabora|procesar
handle|gestisci|manejar
send|invia|enviar
receive|ricevi|recibir
connect|collega|conectar
disconnect|scollega|desconectar
import|importa|importar
export|esporta|exportar
return|ritorna|retornar
exit|esci|salir
cancel|annulla|cancelar
confirm|conferma|confirmar
accept|accetta|aceptar
reject|rifiuta|rechazar
allow|consenti|permitir
deny|nega|denegar
lock|blocca|bloquear
unlock|sblocca|desbloquear
allocate|alloca|asignar
release|rilascia|liberar
memory|memoria|memoria
buffer|buffer|buffer
address|indirizzo|dirección
pointer|puntatore|puntero
reference|riferimento|referencia
object|oggetto|objeto
class|classe|clase
record|record|registro
structure|struttura|estructura
enum|enumerazione|enumeración
type|tipo|tipo
variable|variabile|variable
constant|costante|constante
function|funzione|función
method|metodo|metodo
parameter|parametro|parametro
argument|argomento|argumento
field|campo|campo
property|proprietà|propiedad
item|elemento|elemento
element|elemento|elemento
array|array|arreglo
list|lista|lista
map|mappa|mapa
key|chiave|clave
text|testo|texto
string|stringa|cadena
character|carattere|carácter
number|numero|numero
integer|intero|entero
decimal|decimale|decimal
boolean|booleano|booleano
true|vero|verdadero
false|falso|falso
empty|vuoto|vacio
null|nullo|nulo
left|sinistra|izquierda
right|destra|derecha
top|alto|superior
bottom|basso|inferior
row|riga|fila
column|colonna|columna
line|riga|linea
page|página|página
window|finestra|ventana
screen|schermo|pantalla
view|vista|vista
menu|menu|menu
button|pulsante|botón
label|etichetta|etiqueta
title|titolo|título
icon|icona|icono
color|colore|color
font|carattere|fuente
editor|editor|editor
project|progetto|proyecto
module|modulo|modulo
package|pacchetto|paquete
library|libreria|biblioteca
version|versione|version
profile|profilo|perfil
language|lingua|idioma
locale|localizzazione|configuración_regional
translation|traduzione|traducción
word|parola|palabra
comment|commento|comentario
code|codice|código
token|token|token
lexer|lexer|lexer
parser|parser|parser
syntax|sintassi|sintaxis
semantic|semántica|semántica
runtime|runtime|runtime
compiler|compilatore|compilador
backend|backend|backend
frontend|frontend|frontend
native|nativo|nativo
dynamic|dinamico|dinamico
static|statico|estatico
public|pubblico|público
private|privato|privado
local|locale|local
global|globale|global
internal|interno|interno
external|esterno|externo
main|principale|principal
temporary|temporaneo|temporal
cache|cache|cache
data|dati|datos
config|configurazione|configuración
option|opzione|opción
setting|impostazione|ajuste
mode|modalità|modo
feature|funzionalità|funciónalidad
service|servizio|servicio
engine|motore|motor
client|client|cliente
server|server|servidor
request|richiesta|solicitud
response|risposta|respuesta
command|comando|comando
event|evento|evento
state|stato|estado
node|nodo|nodo
parent|genitore|padre
child|figlio|hijo
root|radice|raiz
head|testa|cabeza
tail|coda|cola
source|sorgente|fuente
destination|destinazione|destino
original|originale|original
canonical|canonico|canonico
extended|esteso|extendido
simple|semplice|simple
advanced|avanzato|avanzado
basic|base|basico
safe|sicuro|seguro
unsafe|non_sicuro|inseguro
fast|veloce|rápido
slow|lento|lento
small|piccolo|pequeño
large|grande|grande
high|alto|alto
low|basso|bajo
positive|positivo|positivo
negative|negativo|negativo
equal|uguale|igual
different|diverso|diferente
found|trovato|encontrado
missing|mancante|faltante
unknown|sconosciuto|desconocido
available|disponibile|disponible
required|richiesto|requerido
optional|opzionale|opciónal
multiple|multiplo|multiple
single|singolo|unico
all|tutto|todo
none|nessuno|ninguno
only|solo|solo
before|prima|antes
after|dopo|después
inside|dentro|dentro
outside|fuori|fuera
with|con|con
without|senza|sin
from|da|desde
to|a|a
into|in|en
for|per|para
of|di|de
and|e|y
or|o|o
not|non|no
"""


def normalize_unicode(text):
    # Keep equivalent Unicode forms stable.
    return unicodedata.normalize("NFC", text)


def _build_vocabulary():
    result = {}
    for raw in _EASY_ROWS.strip().splitlines():
        en, it, es = (normalize_unicode(value) for value in raw.split("|"))
        result[en] = {"en": en, "it": it, "es": es}
    return result


EASY_VOCABULARY = _build_vocabulary()
EASY_VOCABULARY_CAPACITY = 5000


def _language_code(language):
    return language.value if isinstance(language, SourceLanguage) else str(language)


def _target_word(canonical, language):
    code = _language_code(language)
    words = EASY_VOCABULARY.get(canonical)
    if words is not None and code in words:
        return words[code]
    language_words = get_language_data(code).EASY_WORDS
    return language_words.get(canonical, canonical)


def _reverse_map(language):
    code = _language_code(language)
    result = {}
    for canonical, words in EASY_VOCABULARY.items():
        if code in words:
            result[normalize_unicode(words[code]).casefold()] = canonical
    for canonical, localized in get_language_data(code).EASY_WORDS.items():
        result[normalize_unicode(localized).casefold()] = canonical
    return result


def _split_identifier(identifier):
    identifier = normalize_unicode(identifier)
    if "_" in identifier:
        return identifier.split("_"), "snake"
    parts = re.findall(
        r"[^\W\d_]+?(?=[A-ZÀ-ÖØ-Þ]|\d|$)|[^\W\d_]+|\d+",
        identifier,
        flags=re.UNICODE,
    )
    if not parts:
        return [identifier], "plain"
    if identifier[:1].isupper():
        return parts, "pascal"
    if len(parts) > 1:
        return parts, "camel"
    return parts, "plain"


def _join_identifier(parts, style):
    if style == "snake":
        return "_".join(parts)
    if style == "pascal":
        return "".join(part[:1].upper() + part[1:] for part in parts)
    if style == "camel":
        first, *rest = parts
        return first.lower() + "".join(part[:1].upper() + part[1:] for part in rest)
    return parts[0] if parts else ""


def translate_identifier(identifier, source_language, target_language):
    parts, style = _split_identifier(identifier)
    source_map = _reverse_map(source_language)
    target_code = target_language.value if isinstance(target_language, SourceLanguage) else str(target_language)
    translated = []
    hits = 0

    for part in parts:
        canonical = source_map.get(normalize_unicode(part).casefold())
        if canonical is None:
            translated.append(part.lower() if style != "plain" else part)
            continue
        translated.append(_target_word(canonical, target_language))
        hits += 1

    if hits == 0:
        confidence = TranslationConfidence.UNKNOWN
    elif hits == len(parts) == 1:
        confidence = TranslationConfidence.EXACT
    elif hits == len(parts):
        confidence = TranslationConfidence.COMPOSED
    else:
        confidence = TranslationConfidence.PARTIAL

    return EasyTranslation(_join_identifier(translated, style), confidence, hits, len(parts))


def translate_comment(text, source_language, target_language):
    source_map = _reverse_map(source_language)
    target_code = target_language.value if isinstance(target_language, SourceLanguage) else str(target_language)
    total = 0
    hits = 0

    def replace(match):
        nonlocal total, hits
        word = match.group(0)
        total += 1
        canonical = source_map.get(normalize_unicode(word).casefold())
        if canonical is None:
            return word
        hits += 1
        translated = _target_word(canonical, target_language)
        if word[:1].isupper():
            translated = translated[:1].upper() + translated[1:]
        return translated

    result = re.sub(r"[^\W\d_]+", replace, normalize_unicode(text), flags=re.UNICODE)
    if hits == 0:
        confidence = TranslationConfidence.UNKNOWN
    elif hits == total:
        confidence = TranslationConfidence.EXACT
    else:
        confidence = TranslationConfidence.PARTIAL
    return EasyTranslation(result, confidence, hits, total)
