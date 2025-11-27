import React, { useState, useEffect } from 'react';
import { Copy, Check, Music, Youtube, Settings, Code, FileJson, Save, Key } from 'lucide-react';

export default function AutomationConfigBuilder() {
    const [configs, setConfigs] = useState([
        { id: 1, style: "Calm song", channelId: "" },
        { id: 2, style: "Cha3bi", channelId: "" },
        { id: 3, style: "Hot music", channelId: "" },
        { id: 4, style: "Guitar + strong beat", channelId: "" },
        { id: 5, style: "Violin instrument + strong beat + Cha3bi", channelId: "" }
    ]);

    const [apiKeys, setApiKeys] = useState({
        GEMINI_API_KEY: "",
        YOUTUBE_API_KEY: "",
        GOOGLE_DRIVE_CREDENTIALS_FILE: "credentials.json" // Placeholder or path
    });

    const [copied, setCopied] = useState(false);
    const [status, setStatus] = useState("");

    // Load config on mount
    useEffect(() => {
        fetch('http://localhost:5000/api/load-config')
            .then(res => res.json())
            .then(data => {
                if (data.config && data.config.items && data.config.items.length > 0) {
                    setConfigs(data.config.items);
                }
                if (data.apiKeys) {
                    setApiKeys(prev => ({ ...prev, ...data.apiKeys }));
                }
            })
            .catch(err => console.error("Failed to load config:", err));
    }, []);

    const updateField = (index, field, value) => {
        const newConfigs = [...configs];
        newConfigs[index][field] = value;
        setConfigs(newConfigs);
    };

    const updateApiKey = (key, value) => {
        setApiKeys(prev => ({ ...prev, [key]: value }));
    };

    const generateJSON = () => {
        const output = {
            "items": configs.map(item => ({
                "id": item.id,
                "style": item.style,
                "channel_id": item.channelId || "INSERT_CHANNEL_ID_HERE"
            }))
        };
        return JSON.stringify(output, null, 2);
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(generateJSON());
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleSave = () => {
        setStatus("Saving...");
        const payload = {
            items: configs,
            apiKeys: apiKeys
        };

        fetch('http://localhost:5000/api/save-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
            .then(res => res.json())
            .then(data => {
                setStatus(data.message);
                setTimeout(() => setStatus(""), 3000);
            })
            .catch(err => {
                console.error(err);
                setStatus("Error saving configuration");
            });
    };

    return (
        <div className="min-h-screen bg-slate-900 text-slate-100 p-4 md:p-8 font-sans">
            <div className="max-w-6xl mx-auto space-y-8">

                {/* Header */}
                <div className="text-center space-y-2">
                    <div className="flex justify-center mb-4">
                        <div className="p-3 bg-blue-600 rounded-full bg-opacity-20 border border-blue-500">
                            <Settings className="w-8 h-8 text-blue-400" />
                        </div>
                    </div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                        Automation Configuration Builder
                    </h1>
                    <p className="text-slate-400">
                        Map your 5 Music Styles to their specific YouTube Channels & Manage API Keys
                    </p>
                </div>

                <div className="grid md:grid-cols-5 gap-6">

                    {/* Left Column: Inputs */}
                    <div className="md:col-span-3 space-y-6">

                        {/* API Keys Section */}
                        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl">
                            <h2 className="flex items-center gap-2 text-xl font-semibold mb-6 pb-4 border-b border-slate-700">
                                <Key className="w-5 h-5 text-yellow-400" />
                                API Keys & Secrets
                            </h2>
                            <div className="space-y-4">
                                <div>
                                    <label className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-1 block">
                                        Gemini API Key
                                    </label>
                                    <input
                                        type="password"
                                        value={apiKeys.GEMINI_API_KEY}
                                        onChange={(e) => updateApiKey('GEMINI_API_KEY', e.target.value)}
                                        className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-yellow-500"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-1 block">
                                        YouTube Data API Key
                                    </label>
                                    <input
                                        type="password"
                                        value={apiKeys.YOUTUBE_API_KEY}
                                        onChange={(e) => updateApiKey('YOUTUBE_API_KEY', e.target.value)}
                                        className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Style Configuration */}
                        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl">
                            <h2 className="flex items-center gap-2 text-xl font-semibold mb-6 pb-4 border-b border-slate-700">
                                <Music className="w-5 h-5 text-purple-400" />
                                Style Configuration
                            </h2>

                            <div className="space-y-4">
                                {configs.map((item, index) => (
                                    <div key={item.id} className="p-4 bg-slate-900/50 rounded-lg border border-slate-700/50 hover:border-blue-500/50 transition-colors">
                                        <div className="grid gap-4">

                                            {/* Style Input */}
                                            <div>
                                                <label className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-1 block">
                                                    Style {item.id}
                                                </label>
                                                <input
                                                    type="text"
                                                    value={item.style}
                                                    onChange={(e) => updateField(index, 'style', e.target.value)}
                                                    className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-purple-300 focus:outline-none focus:border-purple-500 font-medium"
                                                />
                                            </div>

                                            {/* Channel ID Input */}
                                            <div>
                                                <label className="flex items-center gap-1 text-xs text-slate-500 uppercase font-bold tracking-wider mb-1 block">
                                                    <Youtube className="w-3 h-3" /> Target Channel ID
                                                </label>
                                                <input
                                                    type="text"
                                                    placeholder="UC-xxxxxxxxxxxxxxxxx"
                                                    value={item.channelId}
                                                    onChange={(e) => updateField(index, 'channelId', e.target.value)}
                                                    className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500 transition-colors"
                                                />
                                            </div>

                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Right Column: Actions & JSON */}
                    <div className="md:col-span-2 space-y-6">

                        {/* Save Action */}
                        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl">
                            <h2 className="flex items-center gap-2 text-xl font-semibold mb-4">
                                Actions
                            </h2>
                            <button
                                onClick={handleSave}
                                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-500 text-white rounded-lg font-bold shadow-lg transition-all"
                            >
                                <Save className="w-5 h-5" />
                                Save Configuration
                            </button>
                            {status && (
                                <div className="mt-2 text-center text-sm text-green-400 font-medium">
                                    {status}
                                </div>
                            )}
                        </div>

                        {/* JSON Output */}
                        <div className="sticky top-8 bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl flex flex-col">
                            <div className="flex justify-between items-center mb-4 pb-4 border-b border-slate-700">
                                <h2 className="flex items-center gap-2 text-xl font-semibold">
                                    <FileJson className="w-5 h-5 text-green-400" />
                                    Generated JSON
                                </h2>
                                <button
                                    onClick={handleCopy}
                                    className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium transition-all ${copied
                                            ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                                            : 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/50'
                                        }`}
                                >
                                    {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                    {copied ? 'Copied!' : 'Copy JSON'}
                                </button>
                            </div>

                            <div className="relative group">
                                <div className="absolute top-2 right-2 px-2 py-1 bg-slate-700 rounded text-xs text-slate-400 font-mono">
                                    config.json
                                </div>
                                <textarea
                                    readOnly
                                    value={generateJSON()}
                                    className="w-full h-[400px] bg-slate-950 p-4 rounded-lg font-mono text-xs text-green-400 leading-relaxed resize-none focus:outline-none border border-slate-800"
                                />
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}
