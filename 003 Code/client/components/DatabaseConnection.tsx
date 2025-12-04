import { useState } from 'react';
import { Database, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { toast } from 'sonner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

interface DatabaseConnectionProps {
  isConnected: boolean;
  onConnectionChange: (config: any) => void;
  onDisconnect: (conneced: boolean) => void;
}

export function DatabaseConnection({ isConnected, onConnectionChange, onDisconnect }: DatabaseConnectionProps) {
  const [isConnecting, setIsConnecting] = useState(false);
  const [dbType, setDbType] = useState('postgresql');
  const [config, setConfig] = useState({
    host: 'localhost',
    port: '5432',
    database: 'postgres',
    user: 'admin',
    password: '',
    
  });

  const handleConnect = async () => {
    setIsConnecting(true);
    
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    if (!config.password) {
      toast.error('비밀번호가 필요합니다');
      setIsConnecting(false);
      return;
    }

    onConnectionChange(config);
    setIsConnecting(false);
  };

  const handleDisconnect = async() => {
    setIsConnecting(false);

    onDisconnect(false);
    toast.info('데이터베이스 연결이 해제되었습니다');
  };

  const handleTestConnection = async () => {
    setIsConnecting(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    toast.success('연결 테스트 성공');
    setIsConnecting(false);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Connection Status Card */}
      <Card className={`p-6 border-2 ${isConnected ? 'border-green-300 bg-gradient-to-r from-green-50 to-emerald-50' : 'border-neutral-200'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`flex h-12 w-12 items-center justify-center rounded-full ${
              isConnected ? 'bg-gradient-to-br from-green-500 to-green-600 shadow-md' : 'bg-neutral-200'
            }`}>
              <Database className={`h-6 w-6 ${
                isConnected ? 'text-white' : 'text-neutral-500'
              }`} />
            </div>
            <div>
              <h3>데이터베이스 연결</h3>
              <div className="flex items-center gap-2 mt-1">
                {isConnected ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <span className="text-green-700">연결됨</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 text-neutral-400" />
                    <span className="text-neutral-600">연결 안 됨</span>
                  </>
                )}
              </div>
            </div>
          </div>
          
          {isConnected && (
            <Badge className="bg-gradient-to-r from-green-500 to-green-600 border-0">
              활성
            </Badge>
          )}
        </div>
      </Card>

      {/* Connection Configuration */}
      <Card className="p-6">
        <h3 className="mb-4">연결 설정</h3>
        
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="db-type">데이터베이스 유형</Label>
            <Select value={dbType} onValueChange={setDbType} disabled={isConnected}>
              <SelectTrigger id="db-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="postgresql">PostgreSQL</SelectItem>
                {/* <SelectItem value="mysql">MySQL</SelectItem>
                <SelectItem value="mongodb">MongoDB</SelectItem>
                <SelectItem value="sqlite">SQLite</SelectItem> */}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="host">호스트</Label>
              <Input
                id="host"
                value={config.host}
                onChange={(e) => setConfig({ ...config, host: e.target.value })}
                disabled={isConnected}
                placeholder="localhost"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="port">포트</Label>
              <Input
                id="port"
                value={config.port}
                onChange={(e) => setConfig({ ...config, port: e.target.value })}
                disabled={isConnected}
                placeholder="5432"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="database">데이터베이스 이름</Label>
            <Input
              id="database"
              value={config.database}
              onChange={(e) => setConfig({ ...config, database: e.target.value })}
              disabled={isConnected}
              placeholder="pdf_manager"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="user">사용자 이름</Label>
            <Input
              id="user"
              value={config.user}
              onChange={(e) => setConfig({ ...config, user: e.target.value })}
              disabled={isConnected}
              placeholder="admin"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">비밀번호</Label>
            <Input
              id="password"
              type="password"
              value={config.password}
              onChange={(e) => setConfig({ ...config, password: e.target.value })}
              disabled={isConnected}
              placeholder="비밀번호 입력"
            />
          </div>
        </div>

        <Separator className="my-6" />

        <div className="flex gap-3">
          {!isConnected ? (
            <>
              <Button
                onClick={handleConnect}
                disabled={isConnecting}
                className="flex-1"
              >
                {isConnecting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                연결
              </Button>
              <Button
                variant="outline"
                onClick={handleTestConnection}
                disabled={isConnecting}
              >
                연결 테스트
              </Button>
            </>
          ) : (
            <Button
              variant="destructive"
              onClick={handleDisconnect}
              className="flex-1"
            >
              연결 해제
            </Button>
          )}
        </div>
      </Card>

    </div>
  );
}
