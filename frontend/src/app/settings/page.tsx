"use client";

import { useState, useEffect } from "react";
import { Bell, Phone, CheckCircle, Send, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/layout/page-header";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface NotifSettings {
  notification_phone: string;
  notify_signals: boolean;
  notify_trade_open: boolean;
  notify_trade_close: boolean;
}

const TOGGLES: { key: keyof NotifSettings; label: string; desc: string }[] = [
  {
    key: "notify_signals",
    label: "Buy signal alerts",
    desc: "SMS when a buy signal is generated for a watchlist stock",
  },
  {
    key: "notify_trade_open",
    label: "Trade opened",
    desc: "SMS when a strategy opens a new position",
  },
  {
    key: "notify_trade_close",
    label: "Trade closed",
    desc: "SMS when a strategy closes a position with P&L result",
  },
];

export default function SettingsPage() {
  const [form, setForm] = useState<NotifSettings>({
    notification_phone: "",
    notify_signals: true,
    notify_trade_open: true,
    notify_trade_close: true,
  });
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testStatus, setTestStatus] = useState<"idle" | "sending" | "ok" | "fail">("idle");
  const [testMessage, setTestMessage] = useState("");

  useEffect(() => {
    fetch(`${API}/api/settings`)
      .then((r) => r.json())
      .then((data: NotifSettings) => setForm(data))
      .catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await fetch(`${API}/api/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTestStatus("sending");
    setTestMessage("");
    try {
      const res = await fetch(`${API}/api/settings/test-sms`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Pass the current phone so it works even before saving
        body: JSON.stringify({ phone: form.notification_phone }),
      });
      const data = await res.json();
      setTestStatus(data.ok ? "ok" : "fail");
      setTestMessage(data.message || "");
    } catch {
      setTestStatus("fail");
      setTestMessage("Network error — is the backend reachable?");
    }
    setTimeout(() => setTestStatus("idle"), 8000);
  };

  const setToggle = (key: keyof NotifSettings, val: boolean) =>
    setForm((f) => ({ ...f, [key]: val }));

  return (
    <div className="mx-auto max-w-[760px] space-y-[18px]">
      <PageHeader
        kicker="Grow"
        title="Settings"
        description="Get a text the moment something worth watching happens — so you can learn from each signal as it fires."
      />

      <div className="grid gap-6 max-w-2xl">
        {/* Phone number */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Phone className="h-5 w-5" />
              SMS Notifications
            </CardTitle>
            <CardDescription>
              Receive text messages via AWS SNS — no extra account needed
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Phone number</label>
              <p className="text-xs text-muted-foreground mb-1">
                10-digit US number (e.g. 6185281028) — country code added automatically
              </p>
              <input
                type="tel"
                value={form.notification_phone}
                onChange={(e) =>
                  setForm((f) => ({ ...f, notification_phone: e.target.value }))
                }
                placeholder="10-digit US number"
                className="mt-1 flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring font-mono"
              />
            </div>

            {/* Notification toggles */}
            <div className="space-y-2">
              <p className="text-sm font-medium">Send SMS for</p>
              {TOGGLES.map(({ key, label, desc }) => (
                <div
                  key={key}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <p className="text-sm font-medium">{label}</p>
                    <p className="text-xs text-muted-foreground">{desc}</p>
                  </div>
                  <button
                    role="switch"
                    aria-checked={form[key] as boolean}
                    onClick={() => setToggle(key, !(form[key] as boolean))}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors focus:outline-none ${
                      form[key] ? "bg-primary" : "bg-muted"
                    }`}
                  >
                    <span
                      className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform mt-0.5 ml-0.5 ${
                        form[key] ? "translate-x-5" : "translate-x-0"
                      }`}
                    />
                  </button>
                </div>
              ))}
            </div>

            <div className="flex items-center gap-3 pt-1">
              <Button size="sm" onClick={handleSave} disabled={saving}>
                {saved ? (
                  <>
                    <CheckCircle className="mr-1 h-4 w-4" /> Saved
                  </>
                ) : saving ? (
                  "Saving…"
                ) : (
                  "Save Settings"
                )}
              </Button>

              <div title={!form.notification_phone.trim() ? "Enter a phone number above first" : undefined}>
                <Button
                  size="sm"
                  onClick={handleTest}
                  disabled={testStatus === "sending" || !form.notification_phone.trim()}
                >
                  {testStatus === "sending" ? (
                    "Sending…"
                  ) : testStatus === "ok" ? (
                    <><CheckCircle className="mr-1 h-4 w-4" /> Sent</>
                  ) : testStatus === "fail" ? (
                    <><XCircle className="mr-1 h-4 w-4" /> Failed</>
                  ) : (
                    <><Send className="mr-1 h-4 w-4" /> Send Test SMS</>
                  )}
                </Button>
              </div>
            </div>

            {testStatus === "ok" && testMessage && (
              <p className="text-xs text-bullish">{testMessage}</p>
            )}
            {testStatus === "fail" && (
              <p className="text-xs text-destructive">
                {testMessage || "SMS failed — check the EC2 instance role has sns:Publish permission."}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Info card about SNS */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              How it works
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>
              Notifications use <strong>AWS SNS</strong> — the same AWS account
              already running the app. No Twilio or other third-party accounts needed.
            </p>
            <p>You will receive a text when:</p>
            <ul className="ml-4 list-disc space-y-1">
              <li>A <strong>buy signal</strong> fires for a stock on your watchlist</li>
              <li>A strategy <strong>opens</strong> a paper trade (shows entry price, stop &amp; target)</li>
              <li>A strategy <strong>closes</strong> a trade (shows exit price &amp; P&amp;L)</li>
            </ul>
            <p className="text-xs pt-1">
              AWS SNS charges ~$0.00645 per SMS to US numbers. With typical trading
              activity this is well under $1/month.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
