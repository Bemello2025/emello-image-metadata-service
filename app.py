from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import piexif
import base64
import io
import os
from iptcinfo3 import IPTCInfo

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "✅ Emello Image Metadata Service is live."

@app.route("/write-metadata", methods=["POST"])
def write_metadata():
    try:
        data = request.json

        base64_str = data.get("image_base64")
        if not base64_str:
            return jsonify({"error": "Missing image_base64"}), 400

        # 🔁 Metadata with defaults
        alt_text = data.get("alt_text", "")
        title_tag = data.get("title_tag", "")
        description = data.get("cms_description", "")
        file_name = data.get("filename", "emello-image.jpg")
        pin_description = data.get("pin_description", "")
        associated_article = data.get("associated_article", "")

        # IPTC nested block
        iptc = data.get("iptc_metadata", {})
        object_name = iptc.get("ObjectName", title_tag)
        iptc_keywords = iptc.get("Keywords", [])
        caption_abstract = iptc.get("Caption-Abstract", description)
        special_instructions = iptc.get("SpecialInstructions", "")
        byline = iptc.get("Byline", "Emello Creative Studio")
        copyright_notice = iptc.get("CopyrightNotice", "Emello Ltd. 2025. All rights reserved.")

        # Decode image
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))

        # ▶️ Save EXIF metadata to file
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description.encode("utf-8")
        exif_dict["0th"][piexif.ImageIFD.XPTitle] = title_tag.encode("utf-16le")
        exif_dict["0th"][piexif.ImageIFD.XPComment] = alt_text.encode("utf-16le")
        exif_dict["0th"][piexif.ImageIFD.XPKeywords] = ", ".join(iptc_keywords).encode("utf-16le")
        exif_dict["0th"][piexif.ImageIFD.Artist] = byline.encode("utf-8")
        exif_dict["0th"][piexif.ImageIFD.Copyright] = copyright_notice.encode("utf-8")
        exif_bytes = piexif.dump(exif_dict)

        # 🔄 Save to temp file
        tmp_path = f"/tmp/{file_name}"
        image.save(tmp_path, "jpeg", exif=exif_bytes)

        # ✍️ IPTC Write
        iptc_info = IPTCInfo(tmp_path, force=True)
        iptc_info["object name"] = object_name[:64]
        iptc_info["keywords"] = iptc_keywords[:64]
        iptc_info["by-line"] = byline[:32]
        iptc_info["copyright notice"] = copyright_notice[:128]
        iptc_info["caption/abstract"] = caption_abstract[:200]
        iptc_info["special instructions"] = special_instructions[:256]
        iptc_info.save()

        # 🔁 Return base64 of updated image
        with open(tmp_path, "rb") as f:
            new_encoded = base64.b64encode(f.read()).decode("utf-8")
        os.remove(tmp_path)

        # 🎯 JSON-LD Schema (optional downstream use)
        jsonld = {
            "@context": "https://schema.org",
            "@type": "ImageObject",
            "contentUrl": f"https://emello.com/images/{file_name}",
            "name": title_tag,
            "description": description,
            "caption": pin_description,
            "author": { "@type": "Organization", "name": "Emello" },
            "license": "https://emello.com/usage-guidelines",
            "associatedArticle": associated_article
        }

        return jsonify({
            "image_base64": new_encoded,
            "jsonld": jsonld,
            "status": "success",
            "message": f"Metadata successfully embedded in {file_name}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
