"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  ApiError,
  Frequency,
  NotificationChannel,
  Schedule,
  UpgradeDetail,
} from "../../lib/api";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onUpgrade: (detail: UpgradeDetail) => void;
  repo: string;
};

export default function ScheduledScansModal({ isOpen, onClose, onUpgrade, repo }: Props) {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [frequency, setFrequency] = useState<Frequency>("weekly");
  const [channels, setChannels] = useState<NotificationChannel[]>([{ type: "email", email: "" }]);

  const loadSchedules = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.schedules();
      setSchedules(data.schedules.filter((schedule) => schedule.repo === repo));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [repo]);

  useEffect(() => {
    if (isOpen) {
      setError(null);
      setShowCreateForm(false);
      loadSchedules();
    }
  }, [isOpen, loadSchedules]);

  const run = async (action: () => Promise<unknown>) => {
    setSaving(true);
    setError(null);
    try {
      await action();
      await loadSchedules();
      return true;
    } catch (err) {
      if (err instanceof ApiError && err.upgrade) onUpgrade(err.upgrade);
      else setError((err as Error).message);
      return false;
    } finally {
      setSaving(false);
    }
  };

  const createSchedule = async () => {
    const created = await run(() =>
      api.createSchedule({
        repo,
        frequency,
        notification_channels: channels.filter((channel) =>
          channel.type === "email" ? channel.email : channel.webhook_url
        ),
      })
    );
    if (created) setShowCreateForm(false);
  };

  const updateChannel = (index: number, updates: Partial<NotificationChannel>) => {
    setChannels(channels.map((channel, i) => (i === index ? { ...channel, ...updates } : channel)));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Scheduled scans"
        className="bg-white rounded-xl max-w-3xl w-full max-h-[90vh] flex flex-col text-gray-900"
      >
        <div className="p-6 border-b flex justify-between items-center">
          <div className="min-w-0">
            <h2 className="text-2xl font-bold">📅 Scheduled Scans</h2>
            <p className="text-gray-600 mt-1 break-all">Automate security scanning for {repo}</p>
          </div>
          <button onClick={onClose} aria-label="Close" className="text-gray-400 hover:text-gray-600 text-2xl">
            ×
          </button>
        </div>

        <div className="p-6 overflow-y-auto space-y-6">
          {error && (
            <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </p>
          )}

          {loading ? (
            <p className="text-center text-gray-600 py-6">Loading scheduled scans...</p>
          ) : (
            schedules.map((schedule) => (
              <div key={schedule.schedule_id} className="border rounded-lg p-4 bg-gray-50">
                <div className="flex flex-wrap justify-between gap-3">
                  <div className="text-sm text-gray-600">
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`px-2 py-1 rounded text-xs font-semibold ${
                          schedule.enabled ? "bg-green-100 text-green-800" : "bg-gray-200 text-gray-800"
                        }`}
                      >
                        {schedule.status}
                      </span>
                      <span className="font-medium text-gray-900">{schedule.frequency} scan</span>
                    </div>
                    <p>Next run: {new Date(`${schedule.next_run}Z`).toLocaleString()}</p>
                    <p>Notifications: {schedule.notification_channels.length} channel(s)</p>
                    {schedule.last_run && (
                      <p>
                        Last run: {new Date(`${schedule.last_run}Z`).toLocaleString()} (
                        {schedule.last_result?.status || "unknown"})
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2 items-start">
                    <button
                      disabled={saving}
                      onClick={() =>
                        run(() =>
                          api.updateSchedule(schedule.schedule_id, { enabled: !schedule.enabled })
                        )
                      }
                      className="px-3 py-1 rounded text-sm font-medium bg-yellow-100 text-yellow-800 hover:bg-yellow-200 disabled:opacity-50"
                    >
                      {schedule.enabled ? "Pause" : "Resume"}
                    </button>
                    <button
                      disabled={saving}
                      onClick={() => {
                        if (confirm("Delete this scheduled scan?")) {
                          run(() => api.deleteSchedule(schedule.schedule_id));
                        }
                      }}
                      className="px-3 py-1 rounded text-sm font-medium bg-red-100 text-red-800 hover:bg-red-200 disabled:opacity-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}

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
              <h3 className="font-semibold mb-4">Create Scheduled Scan</h3>

              <label className="block text-sm font-medium text-gray-700 mb-2" htmlFor="frequency">
                Scan Frequency
              </label>
              <select
                id="frequency"
                value={frequency}
                onChange={(event) => setFrequency(event.target.value as Frequency)}
                className="w-full p-2 border rounded-lg mb-4 bg-white"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>

              <p className="block text-sm font-medium text-gray-700 mb-2">Notification Channels</p>
              {channels.map((channel, index) => (
                <div key={index} className="flex flex-wrap gap-2 mb-2">
                  <select
                    aria-label="Channel type"
                    value={channel.type}
                    onChange={(event) =>
                      updateChannel(index, {
                        type: event.target.value as NotificationChannel["type"],
                      })
                    }
                    className="p-2 border rounded-lg bg-white"
                  >
                    <option value="email">Email</option>
                    <option value="discord">Discord</option>
                    <option value="slack">Slack</option>
                    <option value="webhook">Webhook</option>
                  </select>
                  {channel.type === "email" ? (
                    <input
                      type="email"
                      aria-label="Email address"
                      placeholder="your@email.com"
                      value={channel.email || ""}
                      onChange={(event) => updateChannel(index, { email: event.target.value })}
                      className="flex-1 min-w-0 p-2 border rounded-lg bg-white"
                    />
                  ) : (
                    <input
                      type="url"
                      aria-label="Webhook URL"
                      placeholder="https://..."
                      value={channel.webhook_url || ""}
                      onChange={(event) => updateChannel(index, { webhook_url: event.target.value })}
                      className="flex-1 min-w-0 p-2 border rounded-lg bg-white"
                    />
                  )}
                  <button
                    onClick={() => setChannels(channels.filter((_, i) => i !== index))}
                    aria-label="Remove channel"
                    className="px-3 py-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200"
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                onClick={() => setChannels([...channels, { type: "email", email: "" }])}
                className="text-sm text-blue-600 hover:text-blue-800 mb-4"
              >
                + Add Channel
              </button>

              <div className="flex gap-2">
                <button
                  onClick={createSchedule}
                  disabled={saving}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Create Schedule"}
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
      </div>
    </div>
  );
}
