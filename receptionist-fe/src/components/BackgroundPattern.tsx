import { useMemo } from 'react';
import { MessageSquare, Phone, Bot, Headphones, Users, Clock, Star, Send, Mic, Mail, Calendar, CheckCircle, Bell } from 'lucide-react';
import './BackgroundPattern.css';

export function BackgroundPattern() {
  // Create a grid of repeating icons with random rotations (only once on mount)
  const tiles = useMemo(() => {
    const icons = ['phone', 'message', 'robot', 'headphones', 'users', 'clock', 'star', 'send', 'mic', 'mail', 'calendar', 'checkCircle', 'bell'];

    return Array.from({ length: 600 }, (_, i) => {
      const iconType = icons[Math.floor(Math.random() * icons.length)];
      const rotation = Math.random() * 360; // Random rotation 0-360 degrees

      return {
        id: i,
        type: iconType,
        rotation,
        delay: i * 0.05,
      };
    });
  }, []);

  const renderIcon = (type: string) => {
    switch (type) {
      case 'phone':
        return <Phone size={32} />;
      case 'message':
        return <MessageSquare size={32} />;
      case 'robot':
        return <Bot size={32} />;
      case 'headphones':
        return <Headphones size={32} />;
      case 'users':
        return <Users size={32} />;
      case 'clock':
        return <Clock size={32} />;
      case 'star':
        return <Star size={32} />;
      case 'send':
        return <Send size={32} />;
      case 'mic':
        return <Mic size={32} />;
      case 'mail':
        return <Mail size={32} />;
      case 'calendar':
        return <Calendar size={32} />;
      case 'checkCircle':
        return <CheckCircle size={32} />;
      case 'bell':
        return <Bell size={32} />;
      default:
        return null;
    }
  };

  return (
    <div className="background-pattern">
      {tiles.map((tile) => (
        <div
          key={tile.id}
          className="pattern-tile"
          style={{
            '--rotation': `${tile.rotation}deg`,
          } as React.CSSProperties}
        >
          {renderIcon(tile.type)}
        </div>
      ))}
    </div>
  );
}
