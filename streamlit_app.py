import io
import json
from typing import Any, Dict, Optional, Tuple

import streamlit as st
from PIL import Image, ExifTags

# Optional imports handled with graceful fallbacks
try:
	import pytesseract  # type: ignore
	external_ocr_available = True
except Exception:
	external_ocr_available = False

try:
	from langdetect import detect, DetectorFactory  # type: ignore
	DetectorFactory.seed = 0  # deterministic
	language_detection_available = True
except Exception:
	language_detection_available = False

try:
	from iptcinfo3 import IPTCInfo  # type: ignore
	iptc_available = True
except Exception:
	iptc_available = False


def decode_exif(image: Image.Image) -> Dict[str, Any]:
	"""Extract EXIF metadata using Pillow and map tag ids to names."""
	exif_data: Dict[str, Any] = {}
	if not hasattr(image, "_getexif"):
		return exif_data

	raw_exif = image._getexif() or {}
	if not raw_exif:
		return exif_data

	tag_map = {v: k for k, v in ExifTags.TAGS.items()}
	for tag_id, value in raw_exif.items():
		tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
		exif_data[tag_name] = value
	return exif_data


def extract_gps_from_exif(exif: Dict[str, Any]) -> Optional[Tuple[float, float]]:
	"""Decode GPS info from EXIF into decimal degrees if available."""
	gps_ifd = exif.get("GPSInfo")
	if not gps_ifd:
		return None

	def _rational_to_float(r):
		try:
			# Handle PIL rational tuples or objects
			if isinstance(r, tuple) and len(r) == 2:
				return float(r[0]) / float(r[1]) if r[1] else 0.0
			return float(r)
		except Exception:
			return 0.0

	# GPS tags indices per EXIF spec
	gps_tags = {
		0: "GPSVersionID",
		1: "GPSLatitudeRef",
		2: "GPSLatitude",
		3: "GPSLongitudeRef",
		4: "GPSLongitude",
	}

	# Map numeric keys to names when needed
	if 2 in gps_ifd and 4 in gps_ifd:
		lat_ref = gps_ifd.get(1, "N")
		lon_ref = gps_ifd.get(3, "E")
		lat_vals = gps_ifd.get(2)
		lon_vals = gps_ifd.get(4)

		if not lat_vals or not lon_vals:
			return None

		try:
			lat_deg = _rational_to_float(lat_vals[0])
			lat_min = _rational_to_float(lat_vals[1])
			lat_sec = _rational_to_float(lat_vals[2])
			lon_deg = _rational_to_float(lon_vals[0])
			lon_min = _rational_to_float(lon_vals[1])
			lon_sec = _rational_to_float(lon_vals[2])

			lat = lat_deg + (lat_min / 60.0) + (lat_sec / 3600.0)
			lon = lon_deg + (lon_min / 60.0) + (lon_sec / 3600.0)

			if isinstance(lat_ref, bytes):
				lat_ref = lat_ref.decode(errors="ignore")
			if isinstance(lon_ref, bytes):
				lon_ref = lon_ref.decode(errors="ignore")

			if lat_ref.upper() == "S":
				lat = -lat
			if lon_ref.upper() == "W":
				lon = -lon
			return round(lat, 7), round(lon, 7)
		except Exception:
			return None

	return None


def extract_iptc(image_bytes: bytes) -> Dict[str, Any]:
	"""Extract IPTC metadata if library is available; otherwise return empty."""
	if not iptc_available:
		return {}
	try:
		# IPTCInfo expects a file path or a file-like bytes object; io.BytesIO works
		info = IPTCInfo(io.BytesIO(image_bytes), force=True)
		iptc_data: Dict[str, Any] = {}
		for key in info:
			value = info[key]
			try:
				serializable = value.decode("utf-8", errors="ignore") if isinstance(value, (bytes, bytearray)) else value
				iptc_data[str(key)] = serializable
			except Exception:
				iptc_data[str(key)] = str(value)
		return iptc_data
	except Exception:
		return {}


def perform_ocr(image: Image.Image) -> str:
	if not external_ocr_available:
		return ""
	try:
		return pytesseract.image_to_string(image)
	except Exception:
		return ""


def detect_language(text: str) -> Optional[str]:
	if not language_detection_available or not text.strip():
		return None
	try:
		return detect(text)
	except Exception:
		return None


def google_maps_link(lat: float, lon: float) -> str:
	return f"https://www.google.com/maps?q={lat},{lon}"


def main():
	st.set_page_config(page_title="Image Metadata Analyzer", page_icon="🖼️", layout="wide")
	st.title("🖼️ Image Metadata Analyzer")
	st.caption("Extract EXIF/IPTC, decode GPS, run OCR, and detect language.")

	with st.sidebar:
		st.header("Settings")
		ocr_enabled = st.checkbox("Run OCR (requires Tesseract)", value=True)
		lang_detect_enabled = st.checkbox("Detect OCR text language", value=True)

	uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png", "tiff", "webp"]) 
	if not uploaded_file:
		st.info("Upload an image to begin.")
		return

	image_bytes = uploaded_file.read()
	# Keep original image for EXIF/format, use RGB copy for preview/OCR
	original_image = Image.open(io.BytesIO(image_bytes))
	image_rgb = original_image.convert("RGB")

	left, right = st.columns([1, 1])
	with left:
		st.subheader("Preview")
		st.image(image_rgb, use_column_width=True)

	with right:
		st.subheader("Metadata")
		exif = decode_exif(original_image)
		gps = extract_gps_from_exif(exif)
		iptc = extract_iptc(image_bytes)

		meta_summary: Dict[str, Any] = {
			"file_name": uploaded_file.name,
			"format": original_image.format,
			"size": {"width": original_image.width, "height": original_image.height},
			"mode": original_image.mode,
			"exif": exif,
			"iptc": iptc,
		}

		if gps:
			lat, lon = gps
			meta_summary["gps"] = {"latitude": lat, "longitude": lon, "maps_link": google_maps_link(lat, lon)}
			st.success(f"GPS: {lat}, {lon}")
			st.markdown(f"[Open in Google Maps]({google_maps_link(lat, lon)})")
		else:
			st.warning("No GPS info found.")

		# Show a few common EXIF fields if available
		camera_model = exif.get("Model")
		date_time = exif.get("DateTimeOriginal") or exif.get("DateTime")
		if camera_model:
			st.write(f"Camera: {camera_model}")
		if date_time:
			st.write(f"Captured: {date_time}")

		with st.expander("Raw EXIF"):
			st.json(exif)
		with st.expander("Raw IPTC"):
			st.json(iptc)

		# OCR and language detection
		ocr_text = ""
		ocr_status = []
		if ocr_enabled:
			if external_ocr_available:
				ocr_text = perform_ocr(image_rgb)
				if ocr_text.strip():
					st.subheader("OCR Text")
					st.code(ocr_text)
				else:
					st.info("No text detected by OCR.")
			else:
				st.info("pytesseract not installed. See README to enable OCR.")

		lang_code: Optional[str] = None
		if lang_detect_enabled and ocr_text.strip():
			if language_detection_available:
				lang_code = detect_language(ocr_text)
				if lang_code:
					st.write(f"Detected language: {lang_code}")
				else:
					st.info("Could not detect language.")
			else:
				st.info("Language detection package not installed.")

		# Export JSON
		meta_summary["ocr_text"] = ocr_text
		meta_summary["ocr_language"] = lang_code
		json_bytes = json.dumps(meta_summary, ensure_ascii=False, indent=2).encode("utf-8")
		st.download_button(
			label="Download results (JSON)",
			data=json_bytes,
			file_name=(uploaded_file.name.rsplit(".", 1)[0] + "_metadata.json"),
			mime="application/json",
		)

	st.caption(
		"Tip: For GPS on iPhone/Android photos, ensure location was enabled when captured."
	)


if __name__ == "__main__":
	main()


