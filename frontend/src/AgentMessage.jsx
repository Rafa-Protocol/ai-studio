import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  LineChart, Line, PieChart, Pie, Cell, XAxis, Tooltip as RechartsTooltip, 
  ResponsiveContainer, Legend 
} from 'recharts';
import { Activity } from 'lucide-react';

// --- HELPER: TYPEWRITER (Internal to AgentMessage) ---
const Typewriter = ({ text, onTick }) => {
  const [displayedText, setDisplayedText] = useState("");
  const [isComplete, setIsComplete] = useState(false);
  const indexRef = useRef(0);

  useEffect(() => {
    if (!text) return;
    setDisplayedText("");
    indexRef.current = 0;
    setIsComplete(false);

    const timer = setInterval(() => {
      if (indexRef.current < text.length) {
        setDisplayedText((prev) => prev + text.charAt(indexRef.current));
        indexRef.current++;
        if (onTick) onTick(); 
      } else {
        setIsComplete(true);
        clearInterval(timer);
      }
    }, 10); 

    return () => clearInterval(timer);
  }, [text, onTick]);

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

// --- MAIN COMPONENT ---
export const AgentMessage = ({ rawContent, onTick }) => {
  
  // 1. Parsing Logic
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

  // 2. Cyberpunk Palette
  const COLORS = {
    cyan: "#06b6d4",   // cyan-500
    purple: "#a855f7", // purple-500
    green: "#22c55e",  // green-500
    blue: "#3b82f6",   // blue-500
    text: "#9ca3af"    // gray-400
  };

  // 3. Custom HUD Tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#050505]/95 border border-cyan-500/30 p-2 rounded shadow-[0_0_15px_rgba(6,182,212,0.15)] backdrop-blur-sm text-xs font-mono">
          <p className="font-bold text-gray-400 mb-1">{label}</p>
          {payload.map((entry, index) => (
            <div key={index} className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: entry.stroke || entry.payload.fill }}></span>
              <span className="text-gray-200">{entry.name}:</span>
              <span className="font-bold" style={{ color: entry.stroke || entry.payload.fill }}>
                {Number(entry.value).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full flex flex-col gap-4">
      {/* Text Output (with Typing Effect) */}
      <Typewriter text={text} onTick={onTick} />

      {/* Visual Payload */}
      {chart && (
        <div className="w-full max-w-lg bg-[#0a0a0a] border border-[#222] rounded-xl p-5 shadow-2xl relative overflow-hidden group mt-2 animate-in fade-in slide-in-from-bottom-4 duration-700">
          
          {/* Background Glow */}
          <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-3xl -z-10 group-hover:bg-cyan-500/10 transition-all duration-1000"></div>

          {/* Header */}
          <div className="flex justify-between items-center mb-6">
             <h4 className="text-[10px] font-bold text-cyan-500 uppercase tracking-[0.2em] flex items-center gap-2">
                <Activity className="w-3 h-3" /> {chart.title || "MARKET_DATA"}
             </h4>
          </div>
          
          {/* Chart Area */}
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              
              {chart.type === 'line' && (
                <LineChart data={chart.data}>
                  <XAxis 
                    dataKey="day" 
                    stroke={COLORS.text} 
                    fontSize={10} 
                    tickLine={false} 
                    axisLine={false} 
                    tick={{ fill: '#555' }}
                  />
                  <RechartsTooltip cursor={{ stroke: '#333', strokeWidth: 1 }} content={<CustomTooltip />} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '10px', paddingTop: '15px', opacity: 0.7 }} />
                  {chart.keys?.map((key, i) => (
                    <Line
                      key={key}
                      type="monotone"
                      dataKey={key}
                      // Cycle through Neon Colors
                      stroke={chart.colors?.[key] || [COLORS.cyan, COLORS.purple, COLORS.green][i % 3]}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, strokeWidth: 0, fill: '#fff' }}
                      animationDuration={1500}
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
                    innerRadius={50}
                    outerRadius={70}
                    paddingAngle={4}
                    dataKey="value"
                    stroke="none"
                  >
                    {chart.data.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={entry.fill || [COLORS.cyan, COLORS.purple, COLORS.green, COLORS.blue][index % 4]} 
                      />
                    ))}
                  </Pie>
                  <RechartsTooltip content={<CustomTooltip />} />
                  <Legend 
                    verticalAlign="middle" 
                    align="right" 
                    layout="vertical" 
                    iconType="circle" 
                    iconSize={8}
                    wrapperStyle={{ fontSize: '10px', color: '#888' }}
                  />
                </PieChart>
              )}

            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};