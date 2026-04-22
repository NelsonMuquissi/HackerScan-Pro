import { Terminal } from 'lucide-react';

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen w-full flex bg-background">
      {/* Left side - Branded presentation */}
      <div className="hidden lg:flex flex-1 flex-col justify-between p-12 bg-card-bg border-r border-card-border relative overflow-hidden">
        {/* Decorative hacker grid background */}
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none" 
             style={{ backgroundImage: 'linear-gradient(#00ff00 1px, transparent 1px), linear-gradient(90deg, #00ff00 1px, transparent 1px)', backgroundSize: '40px 40px' }}>
        </div>
        
        <div className="relative z-10">
          <h1 className="text-3xl font-mono text-neon-green font-bold flex items-center gap-3">
            <Terminal className="w-8 h-8" />
            HackerScan Pro
          </h1>
          <p className="mt-4 text-gray-400 font-mono text-lg max-w-lg">
            Plataforma de offensive security para automação de testes de penetração e análise de infraestruturas cloud.
          </p>
        </div>

        <div className="relative z-10">
          <div className="flex gap-4 items-center">
             <div className="w-16 h-1 bg-neon-green rounded-full"></div>
             <p className="font-mono text-xs text-neon-green tracking-widest">Acesso Restrito</p>
          </div>
        </div>
      </div>

      {/* Right side - Forms */}
      <div className="flex-1 flex flex-col justify-center items-center p-8 relative">
        {children}
      </div>
    </div>
  );
}
