from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import piexif
import io
import base64

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "✅ Emello Image Metadata Service is live."

@app.route('/write-metadata', methods=['POST'])
def write_metadata():
    data = request.json

    try:
        base64_str = data.get("image_base64")
        if not base64_str:
            return jsonify({"error": "Missing image_base64"}), 400

        # Core metadata
        alt_text = data.get("alt_text", "")
        title_tag = data.get("title_tag", "")
        description = data.get("cms_description", "")
        pin_description = data.get("pin_description", "")
        file_name = data.get("filename", "emello-image.jpg")

        # Extended metadata
        semantic_keywords = data.get("semantic_keywords", [])
        llm_tags = data.get("llm_tags", [])
        combined_keywords = list(set(semantic_keywords + llm_tags))  # deduplicated
        keywords_str = ", ".join(combined_keywords)

        # IPTC-style metadata
        iptc = data.get("iptc_metadata", {})
        object_name = iptc.get("ObjectName", title_tag)
        iptc_keywords = iptc.get("Keywords", [])
        byline = iptc.get("Byline", "Emello Creative Studio")
        copyright_notice = iptc.get("CopyrightNotice", "Emello Ltd. 2025. All rights reserved.")
        caption = iptc.get("Caption-Abstract", description)
        special_instructions = iptc.get("SpecialInstructions", "")

        # Decode base64 image
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))

        # Write EXIF metadata
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = caption.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.XPTitle] = title_tag.encode('utf-16le')
        exif_dict["0th"][piexif.ImageIFD.XPComment] = alt_text.encode('utf-16le')
        exif_dict["0th"][piexif.ImageIFD.XPKeywords] = keywords_str.encode('utf-16le')
        exif_dict["0th"][piexif.ImageIFD.Artist] = byline.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.Copyright] = copyright_notice.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.XPSubject] = object_name.encode('utf-16le')
        exif_dict["0th"][piexif.ImageIFD.XPInstructions] = special_instructions.encode('utf-16le')

        exif_bytes = piexif.dump(exif_dict)
        output = io.BytesIO()
        image.save(output, format="JPEG", exif=exif_bytes)
        encoded_img = base64.b64encode(output.getvalue()).decode("utf-8")

        # JSON-LD schema
        associated_article = data.get("associated_article", "")
        jsonld = {
            "@context": "https://schema.org",
            "@type": "ImageObject",
            "contentUrl": f"https://emello.com/images/{file_name}",
            "name": object_name,
            "description": caption,
            "caption": pin_description,
            "author": {
                "@type": "Organization",
                "name": "Emello"
            },
            "license": "https://emello.com/usage-guidelines",
            "associatedArticle": associated_article
        }

        return jsonify({
            "image_base64": encoded_img,
            "jsonld": jsonld,
            "status": "success",
            "message": f"Metadata embedded in {file_name}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
