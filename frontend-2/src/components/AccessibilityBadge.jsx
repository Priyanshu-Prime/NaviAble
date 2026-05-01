import { useEffect, useState } from "react";
import axios from "axios";

export default function AccessibilityBadge({ feature, size = "md", showLabel = true }) {
  const [featureConfig, setFeatureConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const BASE_URL = process.env.REACT_APP_API_URL;
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await axios.get(`${BASE_URL}/features`);
        setFeatureConfig(res.data);
      } catch (err) {
        console.error("Failed to fetch feature config", err);
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, []);

  if (loading || !featureConfig) return null;

  const config = featureConfig[feature];
  if (!config) return null;

  return (
    <span
      className={`inline-flex items-center gap-1 border rounded-full font-medium ${config.color} ${
        size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-3 py-1"
      }`}
      title={config.label}
    >
      <span>{config.icon}</span>
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}