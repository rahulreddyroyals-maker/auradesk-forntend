import {
  LayoutDashboard,
  Inbox,
  Phone,
  MessageSquare,
  MessagesSquare,
  CalendarCheck,
  CalendarDays,
  BookOpen,
  Sparkles,
  BarChart3,
  Settings,
  CreditCard,
  Users,
  Bot,
  History,
  Plug,
  ScrollText,
  Bell,
  UserCircle2,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

export const navSections: NavSection[] = [
  {
    title: "Overview",
    items: [{ label: "Dashboard", href: "/dashboard", icon: LayoutDashboard }],
  },
  {
    title: "Conversations",
    items: [
      { label: "Inbox", href: "/inbox", icon: Inbox },
      { label: "Calls", href: "/calls", icon: Phone },
      { label: "SMS", href: "/sms", icon: MessageSquare },
      { label: "Chat", href: "/chat", icon: MessagesSquare },
      { label: "Conversation History", href: "/conversation-history", icon: History },
    ],
  },
  {
    title: "Scheduling",
    items: [
      { label: "Appointments", href: "/appointments", icon: CalendarCheck },
      { label: "Calendar", href: "/calendar", icon: CalendarDays },
    ],
  },
  {
    title: "AI Employee",
    items: [
      { label: "AI Employee", href: "/ai-employee", icon: Bot },
      { label: "Knowledge Base", href: "/knowledge-base", icon: BookOpen },
      { label: "Services", href: "/services", icon: Sparkles },
    ],
  },
  {
    title: "Business",
    items: [
      { label: "Patients", href: "/patients", icon: UserCircle2 },
      { label: "Analytics", href: "/analytics", icon: BarChart3 },
      { label: "Team", href: "/team", icon: Users },
      { label: "Billing", href: "/billing", icon: CreditCard },
    ],
  },
  {
    title: "System",
    items: [
      { label: "Integrations", href: "/integrations", icon: Plug },
      { label: "Notifications", href: "/notifications", icon: Bell },
      { label: "Logs", href: "/logs", icon: ScrollText },
      { label: "Settings", href: "/settings", icon: Settings },
    ],
  },
];
