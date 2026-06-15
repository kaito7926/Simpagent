"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle, Search, Shield, Terminal, User } from "lucide-react";

import { ActionButton } from "@/components/account-access/ActionButton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import type { CurrentUser } from "@/lib/auth-session";

type SettingsPageProps = {
  currentUser: CurrentUser;
  adminSettings: { trustedSupervisorEnabled: boolean } | null;
  adminCanWrite: boolean;
  adminBusy: boolean;
  adminError: string | null;
  searchEnabled: boolean;
  onTrustedSupervisorToggle: (enabled: boolean) => void;
};

type SettingsSectionId = "profile" | "roles" | "tools" | "readiness";

const settingsNavigation: Array<{
  id: SettingsSectionId;
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  group: "Account" | "System";
}> = [
  { id: "profile", title: "Profile & Session", icon: User, group: "Account" },
  { id: "roles", title: "Roles & Scopes", icon: Shield, group: "Account" },
  { id: "tools", title: "Tool Availability", icon: Search, group: "System" },
  { id: "readiness", title: "System Readiness", icon: CheckCircle, group: "System" },
];

export function SettingsPage({
  currentUser,
  adminSettings,
  adminCanWrite,
  adminBusy,
  adminError,
  searchEnabled,
  onTrustedSupervisorToggle,
}: SettingsPageProps) {
  const [activeSection, setActiveSection] = React.useState<SettingsSectionId>("profile");

  const groupedNavigation = React.useMemo(() => {
    return {
      Account: settingsNavigation.filter((item) => item.group === "Account"),
      System: settingsNavigation.filter((item) => item.group === "System"),
    };
  }, []);

  const renderContent = () => {
    switch (activeSection) {
      case "profile":
        return <ProfileSection currentUser={currentUser} />;
      case "roles":
        return <RolesSection currentUser={currentUser} />;
      case "tools":
        return (
          <ToolsSection
            adminSettings={adminSettings}
            adminBusy={adminBusy}
            adminCanWrite={adminCanWrite}
            adminError={adminError}
            currentUser={currentUser}
            onTrustedSupervisorToggle={onTrustedSupervisorToggle}
            searchEnabled={searchEnabled}
          />
        );
      case "readiness":
        return <ReadinessSection />;
      default:
        return <ProfileSection currentUser={currentUser} />;
    }
  };

  return (
    <div className="admin-layout">
      <Card className="admin-card">
        <CardHeader>
          <CardTitle>Settings</CardTitle>
          <CardDescription>
            Review your current account, scopes, tool availability, and local runtime status.
          </CardDescription>
        </CardHeader>
        <CardContent className="admin-content">
          {(["Account", "System"] as const).map((group, groupIndex) => (
            <div className="admin-row-stack" key={group}>
              {groupIndex > 0 ? <Separator /> : null}
              <div className="admin-card-copy">
                <p className="small-label">{group}</p>
                <div className="admin-filter-pill-row">
                  {groupedNavigation[group].map((item) => {
                    const Icon = item.icon;
                    return (
                      <ActionButton
                        key={item.id}
                        type="button"
                        variant={activeSection === item.id ? "secondary" : "quiet"}
                        fullWidth={false}
                        className={activeSection === item.id ? "filter-pill filter-pill-active" : "filter-pill"}
                        onClick={() => setActiveSection(item.id)}
                      >
                        <Icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </ActionButton>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {renderContent()}
    </div>
  );
}

function ProfileSection({ currentUser }: { currentUser: CurrentUser }) {
  return (
    <Card className="admin-card">
      <CardHeader>
        <CardTitle>Account Information</CardTitle>
        <CardDescription>Your current session identity and email address.</CardDescription>
      </CardHeader>
      <CardContent className="admin-content">
        <div className="admin-row-stack">
          <Label>Email</Label>
          <div className="scope-list-item">
            <span className="scope-label">{currentUser.email}</span>
            <span className="scope-code">Signed in account</span>
          </div>
        </div>
        <div className="admin-row-stack">
          <Label>Account status</Label>
          <div className="inline-actions flex-wrap">
            <Badge variant={currentUser.is_active ? "success" : "danger"}>
              {currentUser.is_active ? "Active" : "Inactive"}
            </Badge>
            <span className="body-copy">Your account is currently in good standing.</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function RolesSection({ currentUser }: { currentUser: CurrentUser }) {
  return (
    <Card className="admin-card">
      <CardHeader>
        <CardTitle>Role & Scopes</CardTitle>
        <CardDescription>Review your authorization boundaries inside SimpAgent.</CardDescription>
      </CardHeader>
      <CardContent className="admin-content">
        <div className="inline-actions flex-wrap">
          <Badge variant={currentUser.role === "admin" ? "default" : "secondary"}>
            {currentUser.role.toUpperCase()}
          </Badge>
          <span className="body-copy">
            {currentUser.role === "admin"
              ? "This account can open administrative surfaces."
              : "This account is limited to standard user capabilities."}
          </span>
        </div>
        <div className="scope-list">
          {currentUser.scopes.map((scope) => (
            <div className="scope-list-item" key={scope}>
              <span className="scope-label">{scope}</span>
              <span className="scope-code">Granted to the current session</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ToolsSection({
  currentUser,
  adminSettings,
  adminCanWrite,
  adminBusy,
  adminError,
  onTrustedSupervisorToggle,
  searchEnabled,
}: {
  currentUser: CurrentUser;
  adminSettings: { trustedSupervisorEnabled: boolean } | null;
  adminCanWrite: boolean;
  adminBusy: boolean;
  adminError: string | null;
  onTrustedSupervisorToggle: (enabled: boolean) => void;
  searchEnabled: boolean;
}) {
  const pythonEnabled = currentUser.scopes.includes("tool:python");

  return (
    <div className="admin-content">
      <Card className="admin-card">
        <CardHeader>
          <CardTitle>Agent Tools</CardTitle>
          <CardDescription>Capabilities the assistant can use while answering.</CardDescription>
        </CardHeader>
        <CardContent className="admin-content">
          <div className="scope-list-item">
            <div className="inline-actions flex-wrap">
              <Search className="h-4 w-4" />
              <span className="scope-label">Google Search Grounding</span>
              <Badge variant={searchEnabled ? "success" : "secondary"}>
                {searchEnabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>
            <span className="scope-code">
              Allows real-time searches with verifiable citations.
            </span>
          </div>

          <div className="scope-list-item">
            <div className="inline-actions flex-wrap">
              <Terminal className="h-4 w-4" />
              <span className="scope-label">Python Sandbox</span>
              <Badge variant={pythonEnabled ? "success" : "secondary"}>
                {pythonEnabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>
            <span className="scope-code">
              Allows reviewed Python execution inside an isolated runtime.
            </span>
          </div>
        </CardContent>
      </Card>

      {currentUser.role === "admin" ? (
        <Card className="admin-card">
          <CardHeader>
            <CardTitle>Administrative controls</CardTitle>
            <CardDescription>Canonical control point for trusted Python orchestration.</CardDescription>
          </CardHeader>
          <CardContent className="admin-content">
            <div className="scope-list-item">
              <div className="inline-actions flex-wrap">
                <Shield className="h-4 w-4" />
                <span className="scope-label">Trusted supervisor</span>
                <Badge variant={adminSettings?.trustedSupervisorEnabled ? "success" : "warning"}>
                  {adminSettings?.trustedSupervisorEnabled ? "Active" : "Inactive"}
                </Badge>
              </div>
              <span className="scope-code">
                Validates Python activity against orchestration safety policy.
              </span>
            </div>
            {adminError ? (
              <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-100" role="alert">
                {adminError}
              </div>
            ) : null}
            {adminCanWrite ? (
              <div className="admin-card-actions">
                <ActionButton
                  type="button"
                  variant={adminSettings?.trustedSupervisorEnabled ? "quiet" : "secondary"}
                  fullWidth={false}
                  disabled={adminBusy || !adminSettings || adminSettings.trustedSupervisorEnabled}
                  onClick={() => onTrustedSupervisorToggle(true)}
                >
                  {adminBusy && !adminSettings?.trustedSupervisorEnabled ? "Updating..." : "Enable trusted supervisor"}
                </ActionButton>
                <ActionButton
                  type="button"
                  variant={adminSettings?.trustedSupervisorEnabled ? "secondary" : "quiet"}
                  fullWidth={false}
                  disabled={adminBusy || !adminSettings || !adminSettings.trustedSupervisorEnabled}
                  onClick={() => onTrustedSupervisorToggle(false)}
                >
                  {adminBusy && adminSettings?.trustedSupervisorEnabled ? "Updating..." : "Disable trusted supervisor"}
                </ActionButton>
              </div>
            ) : (
              <span className="body-copy">This account can review trusted supervisor status but cannot change it.</span>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function ReadinessSection() {
  return (
    <Card className="admin-card">
      <CardHeader>
        <CardTitle>System Status</CardTitle>
        <CardDescription>Frontend-visible readiness summary for the local stack.</CardDescription>
      </CardHeader>
      <CardContent className="admin-content">
        <div className="scope-list-item">
          <div className="inline-actions flex-wrap">
            <CheckCircle className="h-4 w-4" />
            <span className="scope-label">Operational</span>
          </div>
          <span className="scope-code">
            Backend APIs, session handling, and the frontend shell are responding normally.
          </span>
        </div>
        <div className="scope-list-item">
          <div className="inline-actions flex-wrap">
            <AlertTriangle className="h-4 w-4" />
            <span className="scope-label">Check health from Docker</span>
          </div>
          <span className="scope-code">
            Use container health and logs when local startup appears degraded.
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
