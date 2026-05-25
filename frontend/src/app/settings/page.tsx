"use client";

import { Bell, Key, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Configure your account, notifications, and API connections
        </p>
      </div>

      <div className="grid gap-6 max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Profile
            </CardTitle>
            <CardDescription>Manage your account settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Email</label>
              <input
                type="email"
                defaultValue="user@example.com"
                className="mt-1 flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm ring-ring focus:ring-2 outline-none"
              />
            </div>
            <Button size="sm">Save Changes</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notifications
            </CardTitle>
            <CardDescription>Choose what alerts you receive</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { label: "Buy signal alerts", desc: "Get notified when a new buy signal is generated for your watchlist" },
              { label: "Sentiment spikes", desc: "Alert when a watchlist stock has unusual sentiment activity" },
              { label: "Daily digest", desc: "Receive a daily summary of top trending stocks and signals" },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <p className="text-sm font-medium">{item.label}</p>
                  <p className="text-xs text-muted-foreground">{item.desc}</p>
                </div>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input type="checkbox" defaultChecked className="peer sr-only" />
                  <div className="h-6 w-11 rounded-full bg-muted peer-checked:bg-primary after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all peer-checked:after:translate-x-full"></div>
                </label>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              API Keys
            </CardTitle>
            <CardDescription>Connect external data sources</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { label: "Reddit Client ID", placeholder: "Enter your Reddit app client ID" },
              { label: "Reddit Client Secret", placeholder: "Enter your Reddit app client secret" },
              { label: "Finnhub API Key", placeholder: "Enter your Finnhub API key (optional)" },
            ].map((item) => (
              <div key={item.label}>
                <label className="text-sm font-medium">{item.label}</label>
                <input
                  type="password"
                  placeholder={item.placeholder}
                  className="mt-1 flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm ring-ring focus:ring-2 outline-none"
                />
              </div>
            ))}
            <Button size="sm">Save API Keys</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
