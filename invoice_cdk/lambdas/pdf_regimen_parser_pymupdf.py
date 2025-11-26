import re
import io
from typing import List, Dict, Any, Union

try:
    import fitz  # PyMuPDF
except Exception as e:
    fitz = None  # el error se reportará al usar la clase


class RegimenFiscalPyMuPDFParser:
    """Parser que extrae datos importantes desde una Constancia de Situación Fiscal usando PyMuPDF.

    Métodos públicos:
      - extract_from_file(path) -> dict
      - extract_from_bytes(pdf_bytes) -> dict

    Devuelve diccionario con claves:
      nombre, primerApellido, segundoApellido, razonSocial, Rfc, codigoPostal, regimenFiscal
    """

    REGEX_PATTERNS = [
        re.compile(r"R[eé]gimen(?:es)?(?:\s+Fiscal(?:es)?)?[:\-\s]+(.+)", re.IGNORECASE),
        re.compile(r"R[EÉ]GIMEN(?:ES)?[:\-\s]+(.+)", re.IGNORECASE),
    ]

    def __init__(self):
        if fitz is None:
            # Deferir la excepción hasta que realmente se intente usar el parser
            pass

    def _extract_text_from_path(self, path: str) -> str:
        if fitz is None:
            raise RuntimeError("PyMuPDF (fitz) no está disponible. Instala PyMuPDF.")
        txt = []
        #print(f"Extrayendo texto del PDF en: {path}")
        with fitz.open(path) as doc:
            #print(f"Abriendo PDF: {path}")
            #print(f"Cantidad de páginas: {doc.page_count}")
            for page in doc:
                #print(f"texto {page.get_text("words")}")
                # "text" mode devuelve texto con saltos de línea razonables
                txt.append(page.get_text("text"))
        return "\n".join(txt)

    def _extract_text_from_bytes(self, pdf_bytes: bytes) -> str:
        if fitz is None:
            raise RuntimeError("PyMuPDF (fitz) no está disponible. Instala PyMuPDF.")
        txt = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                txt.append(page.get_text("text"))
        return "\n".join(txt)
 
    def _search_regimenes_in_lines(self, lines) -> Union[List[str], None]:
        is_able_to_fetch = False
        is_regimen = False
        is_fecha_fin = False
        regimenes = []
        count = 2
        for line in lines:
            print(f"{line}")
            if line == 'Obligaciones:':
                return regimenes
            if is_able_to_fetch and count % 2 == 0:
                print(f"Count: {count}")
                regimenes.append(line.strip())
            if is_able_to_fetch:
                count += 1
            if line.startswith("Regímenes:") or line.startswith("Regímenes:"):
                is_regimen = True
            if (line.startswith("Fecha Fin") or line.startswith("Fecha Fin")) and is_regimen:
                is_fecha_fin = True
            if is_regimen and is_fecha_fin:
                is_able_to_fetch = True
            

    def _search_line_patterns(self, lines: List[str], patterns: List[str]) -> Union[str, None]:
        for line in lines:
            for pat in patterns:
                m = pat.search(line)
                if m:
                    val = m.group(1).strip()
                    return re.sub(r"[\s:\-]+$", "", val)
        return None
    
    def _search_line_by_name(self, lines: List[str], patterns: str) -> Union[str, None]:
        m = False
        for line in lines:
            if m:
                return line.strip()
            if line==patterns or line.startswith(patterns):
                m = True        
        return None

    def _extract_all_from_text(self, text: str) -> Dict[str, Any]:
        print(text)
        normalized = re.sub(r"[\t\u00A0]+", " ", text)
        lines = [l.strip() for l in normalized.splitlines() if l.strip()]
        # Corregir patrones para que el primer grupo capture el valor real (nombre completo)
        cp_patterns = [re.compile(r"C[oó]digo\s+Postal[:\-\s]+(\d{4,5})", re.IGNORECASE),
                       re.compile(r"C[oó]digoPostal[:\-\s]+(\d{4,5})", re.IGNORECASE)]
        rfc = (self._search_line_by_name(lines, 'RFC:') or "").upper()
        nombre = ""
        primer_apellido = ""
        segundo_apellido = ""
        razon_social = ""
        if self.es_persona_fisica(rfc):
            nombre = self._search_line_by_name(lines, 'Nombre (s):') or ""
            primer_apellido = self._search_line_by_name(lines, 'Primer Apellido:') or ""
            segundo_apellido = self._search_line_by_name(lines, 'Segundo Apellido:') or ""
            razon_social = nombre + " " + primer_apellido + " " + segundo_apellido
        else:
            razon_social = self._search_line_by_name(lines, 'Denominación/Razón Social:') or ""
        cp = self._search_line_patterns(lines, cp_patterns) or ""
        regimenes = self._search_regimenes_in_lines(lines)
        return {
            "razonSocial": razon_social,
            "Rfc": rfc,
            "codigoPostal": cp,
            "regimenFiscal": regimenes
        }

    def extract_from_file(self, path: str) -> Dict[str, Any]:
        """Extrae datos desde un archivo PDF en disco."""
        text = self._extract_text_from_path(path)
        return self._extract_all_from_text(text)

    def extract_from_bytes(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extrae datos desde bytes PDF."""
        text = self._extract_text_from_bytes(pdf_bytes)
        return self._extract_all_from_text(text)

    def es_persona_fisica(self, rfc: str) -> bool:
        """Determina si el RFC corresponde a una Persona Física por formato RFC."""
        if not rfc or len(rfc) < 12:
            return False
        return bool(re.match(r"^[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}$", rfc, re.IGNORECASE))
