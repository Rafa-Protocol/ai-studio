import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { v4 as uuidv4 } from 'uuid';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useAccount, useSendTransaction, useBalance } from 'wagmi'; 
import { parseEther, formatUnits } from 'viem';
import { LineChart, Line, PieChart, Pie, Cell, XAxis, Tooltip as RechartsTooltip, ResponsiveContainer, Legend } from 'recharts';
import { 
  Wallet, Activity, TrendingUp, Clock, FileText, Hash, Zap, Shield, Disc, Wifi, Loader2 
} from 'lucide-react';
import './App.css';

// --- CONFIGURATION ---
const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// --- SUB-COMPONENT: TYPEWRITER EFFECT ---
const Typewriter = ({ text, onTick, isAgent }) => {
  const [displayedText, setDisplayedText] = useState("");
  const [isComplete, setIsComplete] = useState(false);
  const indexRef = useRef(0);

  useEffect(() => {
    if (!text) return;
    if (!isAgent) {
        setDisplayedText(text);
        setIsComplete(true);
        return;
    }
    setDisplayedText("");
    indexRef.current = 0;
    setIsComplete(false);

    const timer = setInterval(() => {
      if (indexRef.current < text.length) {
        const char = text.charAt(indexRef.current);
        setDisplayedText((prev) => prev + char);
        indexRef.current++;
        if (onTick) onTick(); 
      } else {
        setIsComplete(true);
        clearInterval(timer);
      }
    }, 10); 

    return () => clearInterval(timer);
  }, [text, isAgent, onTick]);

  if (!text) return null;

  return (
    <div className="relative">
        <ReactMarkdown 
            remarkPlugins={[remarkGfm]} 
            components={{
                strong: ({node, ...props}) => <span className="text-cyan-400 font-bold text-shadow-neon" {...props} />,
                code: ({node, inline, ...props}) => <span className="bg-cyan-900/20 border border-cyan-500/20 px-1 py-0.5 rounded text-cyan-200 font-mono text-xs" {...props} />,
                p: ({node, ...props}) => <p className="mb-1 leading-relaxed inline" {...props} />,
                a: ({node, ...props}) => <a className="text-blue-400 underline decoration-dotted hover:text-blue-300" target="_blank" rel="noopener noreferrer" {...props} />
            }}
        >
            {displayedText}
        </ReactMarkdown>
        {!isComplete && <span className="inline-block w-2 h-4 bg-green-500 ml-1 animate-pulse align-middle"></span>}
    </div>
  );
};

// --- COMPONENT: AGENT MESSAGE (HANDLES CHARTS) ---
const AgentMessage = ({ rawContent, onTick }) => {
  const parseMessage = (rawText) => {
    const chartRegex = /\/\/\/ CHART_DATA([\s\S]*?)\/\/\//;
    const match = rawText.match(chartRegex);
    
    if (match) {
      try {
        const chartData = JSON.parse(match[1]);
        const text = rawText.replace(match[0], '').trim(); 
        return { text, chart: chartData };
      } catch (e) {
        console.error("Failed to parse chart JSON", e);
      }
    }
    return { text: rawText, chart: null };
  };

  const { text, chart } = parseMessage(rawContent);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#0a0a0a] border border-[#333] p-2 rounded shadow-xl text-xs font-mono">
          <p className="font-bold text-gray-300 mb-1">{label}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.stroke || entry.payload.fill }}>
              {entry.name}: {entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full">
      <Typewriter text={text} isAgent={true} onTick={onTick} />

      {chart && (
        <div className="mt-4 mb-2 w-full max-w-lg bg-[#0c0c0c] border border-[#222] rounded-lg p-4 animate-in fade-in slide-in-from-bottom-2 duration-700">
          <div className="flex justify-between items-center mb-4">
             <h4 className="text-xs font-bold text-cyan-500 uppercase tracking-widest flex items-center gap-2">
                <Activity className="w-3 h-3" /> {chart.title || "Market Data"}
             </h4>
          </div>
          
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              {chart.type === 'line' && (
                <LineChart data={chart.data}>
                  <XAxis dataKey="day" stroke="#333" fontSize={10} tickLine={false} axisLine={false} />
                  <RechartsTooltip content={<CustomTooltip />} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }} />
                  {chart.keys?.map((key, i) => (
                    <Line
                      key={key}
                      type="monotone"
                      dataKey={key}
                      stroke={chart.colors?.[key] || ["#10b981", "#3b82f6"][i]}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, fill: '#fff' }}
                    />
                  ))}
                </LineChart>
              )}

              {chart.type === 'pie' && (
                <PieChart>
                  <Pie
                    data={chart.data}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={60}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {chart.data.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill || ["#3b82f6", "#10b981", "#f59e0b"][index % 3]} stroke="rgba(0,0,0,0)" />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                  <Legend verticalAlign="right" align="right" layout="vertical" iconType="circle" wrapperStyle={{ fontSize: '10px' }}/>
                </PieChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

// --- SUB-COMPONENT: PORTFOLIO TABLE ---
const PortfolioTable = ({ portfolio, prices }) => {
  return (
    <div className="bg-[#111] border border-[#222] rounded-xl overflow-hidden mt-3">
      <table className="w-full text-left text-[10px] font-mono">
        <thead className="bg-[#1a1a1a] text-gray-500 uppercase font-bold tracking-wider">
          <tr>
            <th className="p-2">Asset</th>
            <th className="p-2">Bal</th>
            <th className="p-2 text-right">USD Value</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#222]">
          {Object.entries(portfolio).map(([asset, qty]) => {
            if (qty <= 0.000001) return null; 
            const price = asset.toUpperCase() === 'USDC' ? 1.0 : (prices?.[asset.toLowerCase()] || 0);
            const value = qty * price;
            
            return (
              <tr key={asset} className="hover:bg-[#161616] transition-colors group">
                <td className="p-2 font-bold text-gray-300 flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${asset === 'ETH' ? 'bg-purple-500' : 'bg-cyan-500'}`}></span>
                    {asset}
                </td>
                <td className="p-2 text-gray-500">{Number(qty).toLocaleString(undefined, { maximumFractionDigits: 4 })}</td>
                <td className="p-2 text-right text-cyan-400 font-bold">
                    {price > 0 
                        ? `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                        : <span className="text-gray-600">Fetching...</span>
                    }
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

const AgentThinking = () => {
  const [step, setStep] = useState(0);
  const thoughts = [
    "📡 ESTABLISHING SECURE UPLINK...",
    "🧠 LOADING QUANT MODELS...",
    "🔍 ANALYZING ON-CHAIN DATA...",
    "🛡️ VERIFYING CONTRACT PERMISSIONS...",
    "⚡ SIMULATING TRANSACTION PATH...",
    "🖊️ SIGNING PAYLOAD VIA CDP...",
    "🚀 BROADCASTING TO NETWORK..."
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setStep((prev) => (prev + 1) % thoughts.length);
    }, 1200); // Change text every 1.2s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-4 mt-4 mb-4 ml-6 animate-in fade-in slide-in-from-left-2 duration-500">
      {/* Custom Cyberpunk Spinner */}
      <div className="relative w-6 h-6">
        <div className="absolute inset-0 border-2 border-t-cyan-500 border-r-transparent border-b-cyan-800 border-l-transparent rounded-full animate-spin"></div>
        <div className="absolute inset-1 border-2 border-t-transparent border-r-green-400 border-b-transparent border-l-green-400 rounded-full animate-spin-reverse"></div>
      </div>
      
      <div className="flex flex-col">
        <span className="text-[10px] text-green-500 font-mono tracking-widest">
           {thoughts[step]}<span className="animate-pulse">_</span>
        </span>
        <span className="text-[8px] text-gray-600 uppercase tracking-wide">
           RUNTIME_EXECUTION_ACTIVE
        </span>
      </div>
    </div>
  );
};

// --- MAIN APP COMPONENT ---
function App() {
  const { address, isConnected } = useAccount();
  const { sendTransaction, isPending: isTxPending } = useSendTransaction();
  
  const [input, setInput] = useState("");
  const [lines, setLines] = useState(() => [
    { id: uuidv4(), type: 'system', text: "RAFA.OS v2.0.4 (stable) [Sepolia-Base]" },
    { id: uuidv4(), type: 'agent', text: "System Online. Connect Wallet to initialize Agent Uplink." }
  ]);
  
  const [isCmdLoading, setIsCmdLoading] = useState(false);
  const [isInitLoading, setIsInitLoading] = useState(false);
  
  const [agentAddress, setAgentAddress] = useState(null);
  const [portfolio, setPortfolio] = useState({});
  const [marketPrices, setMarketPrices] = useState(null);
  const [txLogs, setTxLogs] = useState([]);
  
  const [threadId] = useState(() => uuidv4());
  const bottomRef = useRef(null);
  const hasInitialized = useRef(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [lines, scrollToBottom]);

  const balanceQuery = useBalance({
    address: agentAddress,
    chainId: 84532, 
    query: { enabled: !!agentAddress, refetchInterval: 3000 } 
  });

  const displayPortfolio = { ...portfolio };
  if (balanceQuery.data) {
      const liveEth = Number(formatUnits(balanceQuery.data.value, 18));
      displayPortfolio['ETH'] = liveEth;
  }

  let calculatedTotal = 0;
  let isAumReady = false;

  if (marketPrices) {
      if (balanceQuery.data) {
          const ethQty = Number(formatUnits(balanceQuery.data.value, 18));
          const ethPrice = marketPrices.eth || 0;
          calculatedTotal += (ethQty * ethPrice);
      }
      Object.entries(portfolio).forEach(([asset, qty]) => {
          if (asset.toUpperCase() === 'ETH') return; 
          const price = asset.toUpperCase() === 'USDC' ? 1.0 : (marketPrices[asset.toLowerCase()] || 0);
          calculatedTotal += (qty * price);
      });
      isAumReady = true; 
  }

  const finalTotalDisplay = calculatedTotal.toLocaleString('en-US', { style: 'currency', currency: 'USD' });

  // --- 1. INITIALIZATION EFFECT (FIXED URL) ---
  useEffect(() => {
    if (isConnected && address) {
        if (hasInitialized.current === address) return;
        hasInitialized.current = address;
        setIsInitLoading(true);

        if (!agentAddress) {
            addLine('system', `>> USER IDENTITY CONFIRMED: ${address.slice(0,6)}...`);
        }

        // FIXED: Added /api/ prefix
        axios.post(`${API_BASE_URL}/api/init-user`, { user_address: address })
            .then(res => {
                const data = res.data;
                setAgentAddress(data.agent_address);
                setPortfolio(data.portfolio || {});
                setMarketPrices(data.prices || {});
                
                if (data.trades && data.trades.length > 0) {
                    const formattedLogs = data.trades.map(t => ({
                        hash: t.tx_hash,
                        type: t.side,
                        time: new Date(t.timestamp * 1000).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})
                    })).reverse();
                    setTxLogs(formattedLogs);
                }
                if (data.agent_address) {
                    addLine('success', `>> Agent Online: ${data.agent_address}`);
                }
            })
            .catch(err => {
                console.error(err);
                addLine('error', ">> CONNECTION FAILURE: Backend Unreachable.");
                hasInitialized.current = null; 
            })
            .finally(() => {
                setIsInitLoading(false);
            });
    }
    if (!isConnected) {
        hasInitialized.current = null;
    }
  }, [isConnected, address, agentAddress]);

  const addLine = (type, text) => {
    setLines(prev => [...prev, { id: uuidv4(), type, text }]);
  };

  const handleFundAgent = () => {
    if (!agentAddress) return;
    addLine('system', ">> MANUAL OVERRIDE: Injecting Capital (0.01 ETH)...");
    
    sendTransaction({ 
        to: agentAddress, 
        value: parseEther('0.01') 
    }, {
        onSuccess: (hash) => {
            addLine('success', `>> TX BROADCAST: ${hash}`);
            setTimeout(() => balanceQuery.refetch(), 2000);
        },
        onError: (err) => {
            addLine('error', `>> TX REJECTED: ${err.shortMessage || err.message}`);
        }
    });
  };

  // --- 2. RUN COMMAND (FIXED URLs) ---
  const runCommand = async (e) => {
    e.preventDefault();
    if (!input.trim() || !isConnected) return;

    const cmd = input;
    setLines(prev => [...prev, { id: uuidv4(), type: 'user', text: cmd }]);
    setInput("");
    setIsCmdLoading(true);

    try {
        // FIXED: Added /api/ prefix
        const res = await axios.post(`${API_BASE_URL}/api/run-strategy`, { 
            user_address: address, 
            input: cmd,
            thread_id: threadId 
        });

        const reply = res.data.result || "Command executed."; 
        addLine('agent', reply);
        
        // FIXED: Added /api/ prefix
        axios.post(`${API_BASE_URL}/api/init-user`, { user_address: address })
            .then(updateRes => {
                setPortfolio(updateRes.data.portfolio);
                setMarketPrices(updateRes.data.prices);
            });
        
        balanceQuery.refetch();

        const hashMatch = reply.match(/0x[a-fA-F0-9]{40,64}/);
        if (hashMatch) {
            setTxLogs(prev => [{
                hash: hashMatch[0], 
                type: cmd.toLowerCase().includes("buy") ? "BUY" : "EXEC",
                time: new Date().toLocaleTimeString()
            }, ...prev]);
        }

    } catch (error) {
        addLine('error', ">> EXECUTION ERROR: Agent Lost Connection.");
    } finally {
        setIsCmdLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-[#050505] text-[#a5b6cf] font-mono overflow-hidden selection:bg-cyan-500/30">
      
      {/* SIDEBAR */}
      <div className="w-80 bg-[#0a0a0a] border-r border-[#333] flex flex-col z-20 shadow-2xl">
        <div className="p-6 border-b border-[#222]">
            <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-gradient-to-br from-cyan-900/40 to-blue-900/40 border border-cyan-500/30 rounded-lg flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.15)]">
                    <img src="/favicon.svg" alt="Logo" className="w-6 h-6 text-cyan-400" />
                </div>
                <div>
                    <h1 className="text-xl font-bold text-white tracking-tight leading-none font-sans">
                        RAFA<span className="text-cyan-500"></span>
                    </h1>
                    <span className="text-[10px] text-gray-500 tracking-widest uppercase">
                        AI Studio
                    </span>
                </div>
            </div>

            <div className="mt-4 flex items-center gap-2 bg-[#111] py-1.5 px-3 rounded border border-[#222]">
                <div className={`w-2 h-2 rounded-full shadow-[0_0_8px_currentColor] ${isConnected ? 'bg-green-500 text-green-500 animate-pulse' : 'bg-red-500 text-red-500'}`}></div>
                <span className={`text-[10px] font-bold tracking-wider ${isConnected ? 'text-green-500' : 'text-red-500'}`}>
                    {isConnected ? "SYSTEM_ONLINE" : "DISCONNECTED"}
                </span>
            </div>
        </div>

        <div className="p-5 border-b border-[#222]">
            <label className="text-[10px] uppercase text-gray-500 tracking-widest font-semibold flex items-center gap-2 mb-2">
                <Activity className="w-3 h-3" /> Total AUM
            </label>
            <div className="relative z-10 mb-4">
                {isInitLoading || (!isAumReady && isConnected) ? (
                     <div className="text-xl font-bold text-gray-500 animate-pulse flex items-center gap-2">
                        <Loader2 className="w-5 h-5 animate-spin" /> Analyzing...
                     </div>
                ) : (
                    <div className="text-3xl font-bold text-white tracking-tight">
                        {finalTotalDisplay} 
                    </div>
                )}
                <div className="text-xs text-green-400 mt-1 flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" /> +0.00% (24h)
                </div>
            </div>
            <PortfolioTable portfolio={displayPortfolio} prices={marketPrices || {}} />
        </div>

        <div className="flex-1 flex flex-col min-h-0">
             <div className="px-5 pt-5 pb-2 flex justify-between items-center">
                <label className="text-[10px] uppercase text-gray-500 tracking-widest font-semibold flex items-center gap-2">
                    <FileText className="w-3 h-3" /> Event Log
                </label>
                <span className="text-[10px] text-gray-600">{txLogs.length} Txs</span>
             </div>
             <div className="flex-1 overflow-y-auto px-5 pb-5 space-y-2 custom-scrollbar">
                {txLogs.length === 0 ? (
                    <div className="text-center py-6 text-[10px] text-gray-700 italic border border-dashed border-[#222] rounded">
                        No on-chain activity recorded.
                    </div>
                ) : (
                    txLogs.map((log, i) => (
                        <div key={i} className="bg-[#111] border border-[#222] p-2.5 rounded hover:bg-[#161616] transition-colors group">
                            <div className="flex justify-between items-center mb-1">
                                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${log.type === 'BUY' ? 'bg-green-900/30 text-green-400' : 'bg-blue-900/30 text-blue-400'}`}>
                                    {log.type}
                                </span>
                                <span className="text-[10px] text-gray-600 flex items-center gap-1">
                                    <Clock className="w-2.5 h-2.5" /> {log.time}
                                </span>
                            </div>
                            <div className="flex items-center gap-2 text-[10px] font-mono text-gray-500 mt-1">
                                <Hash className="w-3 h-3 opacity-50" />
                                <a href={`https://sepolia.basescan.org/tx/${log.hash}`} target="_blank" rel="noreferrer" className="hover:text-cyan-400 underline decoration-dotted truncate">
                                    {log.hash.slice(0, 20)}...
                                </a>
                            </div>
                        </div>
                    ))
                )}
             </div>
        </div>

        <div className="p-4 border-t border-[#222] bg-[#0c0c0c] space-y-3">
             <div className="flex justify-center w-full [&>div]:w-full">
                 <ConnectButton.Custom>
                    {({ account, chain, openAccountModal, openConnectModal, mounted }) => {
                        const ready = mounted;
                        if (!ready) return null;
                        if (!account || !chain) {
                            return (
                                <button onClick={openConnectModal} className="w-full py-2 bg-cyan-900/10 hover:bg-cyan-900/20 border border-cyan-500/30 text-cyan-400 text-xs font-bold rounded flex items-center justify-center gap-2 uppercase transition-all">
                                    <Wallet className="w-3 h-3" /> Connect Wallet
                                </button>
                            );
                        }
                        return (
                            <button onClick={openAccountModal} className="w-full py-2 bg-[#111] hover:bg-[#161616] border border-green-500/30 text-green-400 text-xs font-bold rounded flex items-center justify-center gap-2 uppercase transition-all">
                                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                                {account.displayName}
                            </button>
                        );
                    }}
                 </ConnectButton.Custom>
             </div>
             <button 
                onClick={handleFundAgent}
                disabled={!agentAddress || isTxPending}
                className="w-full py-2 bg-purple-900/10 hover:bg-purple-900/20 border border-purple-500/30 text-purple-400 text-xs font-bold rounded flex items-center justify-center gap-2 uppercase disabled:opacity-30 disabled:cursor-not-allowed transition-all"
             >
                <Zap className="w-3 h-3" /> {isTxPending ? "Broadcasting..." : "Add Funds"}
             </button>
        </div>
      </div>

      {/* --- TERMINAL (MAIN) --- */}
      <div className="flex-1 flex flex-col relative bg-[#050505]">
        <div className="h-8 border-b border-[#222] bg-[#0a0a0a] flex items-center justify-between px-4 text-[10px] text-gray-500 select-none">
            <div className="flex gap-4">
                <span className="flex items-center gap-1.5"><Shield className="w-3 h-3 text-green-900" /> SECURE_ENCLAVE</span>
                <span className="flex items-center gap-1.5"><Wifi className="w-3 h-3 text-green-900" /> LATENCY: 12ms</span>
            </div>
            <div className="flex gap-4">
                 <span className="flex items-center gap-1.5 text-cyan-700"><Disc className="w-3 h-3" /> MEM: 42%</span>
                 <span className="animate-pulse text-green-500">●</span>
            </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar pb-20 relative">
             <div className="pointer-events-none absolute inset-0 z-0 opacity-5 bg-[url('https://grainy-gradients.vercel.app/noise.svg')]"></div>
             <div className="pointer-events-none absolute inset-0 z-0 scanlines fixed top-0 left-0 w-full h-full"></div>

             {lines.map((line) => (
                <div key={line.id} className="relative z-10 break-words font-mono text-sm group">
                    {line.type === 'user' ? (
                        <div className="mt-4 mb-2 text-white font-bold flex items-start gap-3 fade-in">
                             <div className="mt-1 text-green-500">➜</div>
                             <div className="bg-[#111] px-3 py-2 rounded-r-xl rounded-bl-xl border-l-2 border-green-500">
                                <span className="text-green-500 mr-2 text-xs opacity-50 select-none block mb-1">investor@rafa:~$</span>
                                {line.text}
                             </div>
                        </div>
                    ) : (
                        <div className={`pl-4 border-l-2 ${line.type === 'error' ? 'border-red-500/50 text-red-400' : 'border-cyan-500/30 text-cyan-100'} py-1 ml-2`}>
                            {line.type === 'system' && <span className="text-gray-600 text-[10px] uppercase tracking-wider mb-1 block select-none">System Log</span>}
                            
                            {line.type === 'agent' ? (
                                <AgentMessage 
                                    rawContent={line.text} 
                                    onTick={scrollToBottom} 
                                />
                            ) : (
                                <Typewriter 
                                    text={line.text} 
                                    isAgent={false} 
                                    onTick={scrollToBottom} 
                                />
                            )}
                        </div>
                    )}
                </div>
             ))}
             
             {isCmdLoading && <AgentThinking />}
             <div ref={bottomRef} />
        </div>

        <div className="p-4 bg-[#0a0a0a] border-t border-[#333] relative z-20 shadow-[0_-5px_15px_rgba(0,0,0,0.5)]">
            <form onSubmit={runCommand} className="flex items-center gap-3 bg-[#050505] border border-[#222] p-3 rounded-md focus-within:border-cyan-500/50 transition-colors">
                <span className="text-green-500 font-bold text-sm animate-pulse">➜</span>
                <input 
                    type="text" 
                    value={input} 
                    onChange={(e) => setInput(e.target.value)} 
                    disabled={!isConnected || isCmdLoading}
                    className="flex-1 bg-transparent text-white focus:outline-none placeholder-gray-700 font-bold caret-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed" 
                    placeholder={isConnected ? "Enter strategy command..." : "Waiting for Neural Link (Connect Wallet)..."} 
                    autoFocus 
                    spellCheck="false"
                    autoComplete="off"
                />
            </form>
        </div>
      </div>
    </div>
  );
}

export default App;