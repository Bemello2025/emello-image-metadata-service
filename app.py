# top of file
import tempfile, uuid

def xp(txt):            # XP* EXIF helper
    return txt.encode("utf-16le") + b"\x00\x00"

@app.route("/write-metadata", methods=["POST"])
def write_metadata():
    try:
        data = request.json or {}

        base64_str = data.get("image_base64", "")
        if base64_str.startswith("data:"):
            base64_str = base64_str.split(",", 1)[1]
        if not base64_str:
            return jsonify({"error": "Missing image_base64"}), 400

        # ... same defaults block ...

        # ── Decode image ──────────────────────────────────────────────
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))
        if image.mode in ("RGBA", "LA"):
            image = image.convert("RGB")

        # ── EXIF ──────────────────────────────────────────────────────
        exif = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        exif["0th"][piexif.ImageIFD.ImageDescription] = description.encode("utf-8")
        exif["0th"][piexif.ImageIFD.XPTitle]    = xp(title_tag)
        exif["0th"][piexif.ImageIFD.XPComment]  = xp(alt_text)
        exif["0th"][piexif.ImageIFD.XPKeywords] = xp(", ".join(iptc_keywords))
        exif["0th"][piexif.ImageIFD.Artist]     = byline.encode("utf-8")
        exif["0th"][piexif.ImageIFD.Copyright]  = copyright_notice.encode("utf-8")
        exif_bytes = piexif.dump(exif)

        # ── Unique temp file ─────────────────────────────────────────
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg",
                                         prefix=f"emello_{uuid.uuid4()}_") as tmp:
            tmp_path = tmp.name
        image.save(tmp_path, "jpeg", exif=exif_bytes)

        # ── IPTC ──────────────────────────────────────────────────────
        iptc_info = IPTCInfo(tmp_path, force=True)
        iptc_info["object name"]        = object_name.encode("utf-8")[:64]
        iptc_info["keywords"]           = [kw.encode("utf-8") for kw in iptc_keywords[:64]]
        iptc_info["by-line"]            = byline.encode("utf-8")[:32]
        iptc_info["caption/abstract"]   = caption_abstract.encode("utf-8")[:200]
        iptc_info["copyright notice"]   = copyright_notice.encode("utf-8")[:128]
        iptc_info["special instructions"] = special_instructions.encode("utf-8")[:256]
        # remove / map any non-standard keys here
        iptc_info.save()

        with open(tmp_path, "rb") as f:
            new_encoded = base64.b64encode(f.read()).decode("utf-8")
        os.remove(tmp_path)

        # ── JSON-LD (unchanged, but wrap associatedArticle properly) ─
        jsonld = {
            "@context": "https://schema.org",
            "@type": "ImageObject",
            "contentUrl": f"https://emello.com/images/{file_name}",
            "name": title_tag,
            "description": description,
            "caption": pin_description,
            "author": {"@type": "Organization", "name": "Emello"},
            "license": "https://emello.com/usage-guidelines",
            "associatedArticle": (
                {"@type": "Article", "url": associated_article}
                if associated_article else None
            )
        }

        return jsonify({
            "image_base64": new_encoded,
            "jsonld": jsonld,
            "status": "success",
            "message": f"Metadata successfully embedded in {file_name}"
        })

    except Exception as e:
        # guarantee temp file is removed
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
        return jsonify({"error": str(e)}), 500
