import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { num2 } from "../lib/l10n";
import { useAppState } from "../lib/state";
import { Icon, Spinner, TLScaffold, pickFile, useShowError } from "../ui";

const base = import.meta.env.BASE_URL;

export default function Connect() {
  const s = useAppState();
  const navigate = useNavigate();
  const showError = useShowError(s);
  const [uploading, setUploading] = useState(false);
  const [paste, setPaste] = useState("");

  const upload = useCallback(
    async (file: Blob, name: string, detect = false) => {
      setUploading(true);
      try {
        const doc = await s.api.uploadDocument(s.userId!, file, name, detect ? null : "utility_bill");
        s.lastDocument = doc;
        if (doc.extracted_fields != null) s.extractedBills.push({ document_type: doc.document_type, ...doc.extracted_fields });
        s.notify();
      } catch (e) {
        showError(e);
      } finally {
        setUploading(false);
      }
    },
    [s, showError],
  );

  // A bill photo can be dropped anywhere on the page
  const uploadRef = useRef(upload);
  uploadRef.current = upload;
  useEffect(() => {
    const over = (e: DragEvent) => e.preventDefault();
    const drop = (e: DragEvent) => {
      e.preventDefault();
      const f = e.dataTransfer?.files?.[0];
      if (f) uploadRef.current(f, f.name, true);
    };
    document.addEventListener("dragover", over);
    document.addEventListener("drop", drop);
    return () => {
      document.removeEventListener("dragover", over);
      document.removeEventListener("drop", drop);
    };
  }, []);

  const importSampleSms = async () => {
    // Demo: synthetic SMS bundled with the app. The phone app reads SMS on the device.
    try {
      const data = await (await fetch(`${base}demo/moon_sms.json`)).json();
      s.sms = data.sms as string[];
      s.notify();
    } catch (e) {
      showError(e);
    }
  };

  const usePasted = async (text: string) => {
    s.sms = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
    s.notify();
    if (s.personaKey === "real_user") {
      try {
        const res = await s.api.uploadSms(s.userId!, { rawText: text });
        s.extractedTransactions = res.transactions;
        s.notify();
      } catch (e) {
        showError(e);
      }
    }
  };

  const pickSmsFile = async () => {
    const f = await pickFile(".txt,.csv,.xml,text/plain,text/csv,text/xml");
    if (!f) return;
    if (s.personaKey === "real_user") {
      try {
        const res = await s.api.uploadSms(s.userId!, { file: f.file, filename: f.name });
        s.extractedTransactions = res.transactions;
        s.sms = s.extractedTransactions.map((t) => JSON.stringify(t));
        s.notify();
      } catch (e) {
        showError(e);
      }
    } else {
      await usePasted(await f.file.text());
    }
  };

  const uploadSample = async () => {
    try {
      const blob = await (await fetch(`${base}demo/desco_bill.jpg`)).blob();
      await upload(blob, "desco_bill.jpg");
    } catch (e) {
      showError(e);
    }
  };

  const pickPhoto = async (camera: boolean) => {
    const f = await pickFile("image/jpeg,image/png,image/webp,application/pdf", camera);
    if (f) await upload(f.file, f.name, true);
  };

  const status = (done: boolean) =>
    done ? <Icon name="check_circle" color="var(--good)" label="done" /> : <Icon name="unchecked" label="not yet" />;

  const fields = s.lastDocument?.extracted_fields;
  const docLabel =
    fields == null
      ? null
      : `${s.t("bill_done")}: ${fields.provider ?? fields.merchant_or_platform ?? fields.shop_name ?? ""} · ৳${fields.amount_bdt ?? fields.page_total_bdt ?? ""}`;

  const toReview = s.personaKey === "real_user" && (s.extractedTransactions.length > 0 || s.extractedBills.length > 0);

  return (
    <TLScaffold
      state={s}
      title={s.t("connect_title")}
      bottom={
        <button className="btn btn-filled" data-testid="get_score" onClick={() => navigate(toReview ? "/review" : "/processing")}>
          {toReview ? s.t("review_title") : s.t("get_score")}
        </button>
      }
    >
      {s.consents.has("sms") && (
        <>
          <button className="card tile list-tile" data-testid="import_sms" onClick={importSampleSms}>
            <Icon name="sms" />
            <div className="tile-text">
              <div className="tile-title">{s.t("import_sms")}</div>
              {s.sms.length > 0 && <div className="tile-subtitle">{`${num2(s.sms.length, s.lang)} ${s.t("sms_loaded")}`}</div>}
            </div>
            {status(s.sms.length > 0)}
          </button>
          <div className="card pad">
            <p className="muted">{s.t("web_sms_note")}</p>
            <textarea
              data-testid="sms_paste"
              className="input"
              rows={3}
              value={paste}
              placeholder={s.t("paste_sms_hint")}
              onChange={(e) => setPaste(e.target.value)}
            />
            <div className="wrap">
              <button className="btn btn-outlined" data-testid="use_pasted" onClick={() => usePasted(paste)}>
                {s.t("use_pasted")}
              </button>
              <button className="btn btn-outlined" data-testid="sms_txt" onClick={pickSmsFile}>
                <Icon name="upload_file" size={18} /> {s.t("upload_txt")}
              </button>
            </div>
          </div>
        </>
      )}
      {(s.consents.has("ocr") || s.consents.has("bills")) && (
        <>
          <button className="card tile list-tile" data-testid="upload_bill" disabled={uploading} onClick={uploadSample}>
            <Icon name="receipt" />
            <div className="tile-text">
              <div className="tile-title">{s.t("upload_bill")}</div>
              {docLabel && <div className="tile-subtitle">{docLabel}</div>}
            </div>
            {uploading ? <Spinner /> : status(fields != null)}
          </button>
          <div className="wrap center-v">
            <button className="btn btn-outlined" data-testid="pick_photo" disabled={uploading} onClick={() => pickPhoto(false)}>
              <Icon name="photo_library" size={18} /> {s.t("choose_photo")}
            </button>
            <button className="btn btn-outlined" data-testid="camera_photo" disabled={uploading} onClick={() => pickPhoto(true)}>
              <Icon name="camera" size={18} /> {s.t("take_photo")}
            </button>
            <span className="muted small">{s.t("drop_hint")}</span>
          </div>
        </>
      )}
    </TLScaffold>
  );
}
