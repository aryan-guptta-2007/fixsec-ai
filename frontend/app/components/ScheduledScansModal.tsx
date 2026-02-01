"use client";

import { useState, useEffect } from "react";

type NotificationChannel = {
  type: "email" | "discord" | "slack" | "webhook";
  email?: string;
  webhook_url?: string;
  custom_payload?: any;
};

type ScheduledScan = {
  schedule_id: string;
  repo: string;
  frequency: "daily" | "weekly" | "monthly";
  notification_channels: NotificationChannel[];
  enabled: boolean;
  next_run: string;
  last_run?: string;
  run_count: number;
  status: string;
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  repo: string;
  token: string;
};

const API = process.env.NEXT_PUBLIC_API_URL;

export default function ScheduledScansModal({ isOpen, onClose, repo, token }: Props) {
  const [schedules, setSchedules] = useState<ScheduledScan[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  
  // Form state
  const [frequency, setFrequency] = useState<"daily" | "weekly" | "monthly">("weekly");
  const [notificationChannels, setNotificationChannels] = useState<NotificationChannel[]>([
    { type: "email", email: "" }
  ]);

  useEffect(() => {
    if (isOpen) {
      loadSchedules();
    }
  }, [isOpen]);

  const loadSchedules = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/schedule/list`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      
      // Filter schedules for this repo
      const repoSchedules = data.schedules?.filter((s: ScheduledScan) => s.repo === repo) || [];
      setSchedules(repoSchedules);
    } catch (err) {
      console.error("Failed to load schedules:", err);
    } finally {
      setLoading(false);
    }
  };

  const createSchedule = async () => {
    try {
      const res = await fetch(`${API}/schedule/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          repo,
          frequency,
          notification_channels: notificationChannels.filter(ch => 
            (ch.type === "email" && ch.email) || 
            (ch.type !== "email" && ch.webhook_url)
          ),
          enabled: true
        }),
      });

      if (res.ok) {
        setShowCreateForm(false);
        loadSchedules();
        alert("✅ Scheduled scan created successfully!");
      } else {
        const error = await res.json();
        alert(`❌ Failed to create schedule: ${error.detail}`);
      }
    } catch (err) {
      console.error("Create schedule error:", err);
      alert("❌ Failed to create schedule");
    }
  };

  const toggleSchedule = async (scheduleId: string, enabled: boolean) => {
    try {
      const res = await fetch(`${API}/schedule/${scheduleId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ enabled }),
      });

      if (res.ok) {
        loadSchedules();
      }
    } catch (err) {
      console.error("Toggle schedule error:", err);
    }
  };

  const deleteSchedule = async (scheduleId: string) => {
    if (!confirm("Are you sure you want to delete this scheduled scan?")) return;

    try {
      const res = await fetch(`${API}/schedule/${scheduleId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        loadSchedules();
        alert("✅ Schedule deleted successfully!");
      }
    } catch (err) {
      console.error("Delete schedule error:", err);
      alert("❌ Failed to delete schedule");
    }
  };

  const addNotificationChannel = () => {
    setNotificationChannels([...notificationChannels, { type: "email", email: "" }]);
  };

  const updateNotificationChannel = (index: number, updates: Partial<NotificationChannel>) => {
    const updated = [...notificationChannels];
    updated[index] = { ...updated[index], ...updates };
    setNotificationChannels(updated);
  };

  const removeNotificationChannel = (index: number) => {
    setNotificationChannels(notificationChannels.filter((_, i) => i !== index));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b bg-gradient-to-r from-purple-50 to-blue-50">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">📅 Scheduled Scans</h2>
              <p className="text-gray-600 mt-1">Automate security scanning for {repo}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading scheduled scans...</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Existing Schedules */}
              {schedules.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-900 mb-4">Active Schedules</h3>
                  <div className="space-y-3">
                    {schedules.map((schedule) => (
                      <div key={schedule.schedule_id} className="border rounded-lg p-4 bg-gray-50">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className={`px-2 py-1 rounded text-xs font-semibold ${
                                schedule.enabled ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"
                              }`}>
                                {schedule.status}
                              </span>
                              <span className="text-sm font-medium text-gray-900">
                                {schedule.frequency.toUpperCase()} SCAN
                              </span>
                            </div>
                            <p className="text-sm text-gray-600">
                              Next run: {new Date(schedule.next_run).toLocaleString()}
                            </p>
                            <p className="text-sm text-gray-600">
                              Notifications: {schedule.notification_channels.length} channels
                            </p>
                            {schedule.last_run && (
                              <p className="text-sm text-gray-600">
                                Last run: {new Date(schedule.last_run).toLocaleString()} ({schedule.run_count} total)
                              </p>
                            )}
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={() => toggleSchedule(schedule.schedule_id, !schedule.enabled)}
                              className={`px-3 py-1 rounded text-sm font-medium ${
                                schedule.enabled
                                  ? "bg-yellow-100 text-yellow-800 hover:bg-yellow-200"
                                  : "bg-green-100 text-green-800 hover:bg-green-200"
                              }`}
                            >
                              {schedule.enabled ? "Pause" : "Resume"}
                            </button>
                            <button
                              onClick={() => deleteSchedule(schedule.schedule_id)}
                              className="px-3 py-1 rounded text-sm font-medium bg-red-100 text-red-800 hover:bg-red-200"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Create New Schedule */}
              {!showCreateForm ? (
                <div className="text-center">
                  <button
                    onClick={() => setShowCreateForm(true)}
                    className="px-6 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700"
                  >
                    + Create New Schedule
                  </button>
                </div>
              ) : (
                <div className="border rounded-lg p-4 bg-blue-50">
                  <h3 className="font-semibold text-gray-900 mb-4">Create Scheduled Scan</h3>
                  
                  {/* Frequency Selection */}
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Scan Frequency
                    </label>
                    <select
                      value={frequency}
                      onChange={(e) => setFrequency(e.target.value as any)}
                      className="w-full p-2 border rounded-lg"
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                  </div>

                  {/* Notification Channels */}
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Notification Channels
                    </label>
                    {notificationChannels.map((channel, index) => (
                      <div key={index} className="flex gap-2 mb-2">
                        <select
                          value={channel.type}
                          onChange={(e) => updateNotificationChannel(index, { 
                            type: e.target.value as any,
                            email: e.target.value === "email" ? channel.email : undefined,
                            webhook_url: e.target.value !== "email" ? channel.webhook_url : undefined
                          })}
                          className="p-2 border rounded-lg"
                        >
                          <option value="email">Email</option>
                          <option value="discord">Discord</option>
                          <option value="slack">Slack</option>
                          <option value="webhook">Webhook</option>
                        </select>
                        
                        {channel.type === "email" ? (
                          <input
                            type="email"
                            placeholder="your@email.com"
                            value={channel.email || ""}
                            onChange={(e) => updateNotificationChannel(index, { email: e.target.value })}
                            className="flex-1 p-2 border rounded-lg"
                          />
                        ) : (
                          <input
                            type="url"
                            placeholder="https://webhook-url.com"
                            value={channel.webhook_url || ""}
                            onChange={(e) => updateNotificationChannel(index, { webhook_url: e.target.value })}
                            className="flex-1 p-2 border rounded-lg"
                          />
                        )}
                        
                        <button
                          onClick={() => removeNotificationChannel(index)}
                          className="px-3 py-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                    
                    <button
                      onClick={addNotificationChannel}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      + Add Channel
                    </button>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <button
                      onClick={createSchedule}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      Create Schedule
                    </button>
                    <button
                      onClick={() => setShowCreateForm(false)}
                      className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}