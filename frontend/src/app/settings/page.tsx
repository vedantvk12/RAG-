"use client"

import { useAuth } from "@/hooks/use-auth"
import { User, Shield, Bell, Key, CreditCard } from "lucide-react"

export default function SettingsPage() {
  const { user } = useAuth()
  
  const email = user?.email || "admin@enterprise.ai"

  return (
    <div className="flex w-full flex-col max-w-[1150px] mx-auto animate-in fade-in duration-300 pb-12 pt-8">
      {/* HEADER SECTION */}
      <div className="flex flex-col space-y-2 mb-8">
        <h2 className="text-[28px] md:text-[30px] font-semibold tracking-[-0.025em] text-[#111111] leading-tight">
          Settings
        </h2>
        <p className="text-[13px] text-[#525252] leading-relaxed">
          Manage your workspace preferences, security and access.
        </p>
      </div>
      
      <div className="flex flex-col md:flex-row gap-10">
        
        {/* Navigation Sidebar (200-220px) */}
        <div className="w-full md:w-[210px] shrink-0 flex flex-col space-y-1">
          <button className="flex items-center gap-2 px-[10px] h-[36px] rounded-[6px] bg-[#111111] text-white text-[13px] font-medium transition-all relative">
            <div className="absolute left-0 top-[8px] bottom-[8px] w-[2px] bg-white rounded-r-sm" />
            <User className="h-[15px] w-[15px] text-white" strokeWidth={1.7} /> Account
          </button>
          <button className="flex items-center gap-2 px-[10px] h-[36px] rounded-[6px] bg-transparent text-[#737373] hover:bg-[#F5F5F5] hover:text-[#111111] text-[13px] font-medium transition-all group">
            <Shield className="h-[15px] w-[15px] text-[#737373] group-hover:text-[#111111]" strokeWidth={1.7} /> Security
          </button>
          <button className="flex items-center gap-2 px-[10px] h-[36px] rounded-[6px] bg-transparent text-[#737373] hover:bg-[#F5F5F5] hover:text-[#111111] text-[13px] font-medium transition-all group">
            <Key className="h-[15px] w-[15px] text-[#737373] group-hover:text-[#111111]" strokeWidth={1.7} /> API Keys
          </button>
          <button className="flex items-center gap-2 px-[10px] h-[36px] rounded-[6px] bg-transparent text-[#737373] hover:bg-[#F5F5F5] hover:text-[#111111] text-[13px] font-medium transition-all group">
            <Bell className="h-[15px] w-[15px] text-[#737373] group-hover:text-[#111111]" strokeWidth={1.7} /> Notifications
          </button>
          <button className="flex items-center gap-2 px-[10px] h-[36px] rounded-[6px] bg-transparent text-[#737373] hover:bg-[#F5F5F5] hover:text-[#111111] text-[13px] font-medium transition-all group">
            <CreditCard className="h-[15px] w-[15px] text-[#737373] group-hover:text-[#111111]" strokeWidth={1.7} /> Billing
          </button>
        </div>

        {/* Settings Content */}
        <div className="flex-1 flex flex-col space-y-6 max-w-[700px]">
          
          <div className="rounded-[8px] border border-[#E5E5E5] bg-[#FFFFFF] p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition-all duration-200">
            <h3 className="text-[16px] font-semibold text-[#111111] mb-1">Profile Information</h3>
            <p className="text-[13px] text-[#737373] mb-5">Update your account's profile information and email address.</p>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[12px] font-medium text-[#111111]">Email Address</label>
                <input 
                  type="email" 
                  disabled
                  defaultValue={email}
                  className="w-full h-[38px] px-3 rounded-[6px] bg-[#F5F5F5] border-transparent text-[13px] text-[#737373] cursor-not-allowed transition-all duration-150"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[12px] font-medium text-[#111111]">Full Name</label>
                <input 
                  type="text" 
                  defaultValue="Platform Administrator"
                  className="w-full h-[38px] px-3 rounded-[6px] bg-white border border-[#D4D4D4] text-[13px] focus:outline-none focus:border-[#171717] focus:ring-0 shadow-sm focus:shadow-[0_0_0_2px_rgba(0,0,0,0.06)] transition-all duration-150"
                />
              </div>
              
              <div className="pt-2 flex justify-end">
                <button className="h-[36px] px-4 rounded-[6px] bg-[#050505] text-white text-[13px] font-medium hover:bg-[#1A1A1A] hover:-translate-y-[1px] hover:shadow-[0_3px_8px_rgba(0,0,0,0.08)] active:scale-[0.98] transition-all duration-200">
                  Save Changes
                </button>
              </div>
            </div>
          </div>

          <div className="rounded-[8px] border border-[#F1C7C7] bg-[#FFFFFF] p-5 transition-all duration-200">
            <h3 className="text-[16px] font-semibold text-[#B91C1C] mb-1">Danger Zone</h3>
            <p className="text-[13px] text-[#737373] mb-5">Permanently delete your workspace and all associated data.</p>
            
            <button className="h-[36px] px-4 rounded-[6px] bg-[#FFFFFF] border border-[#FCA5A5] text-[#B91C1C] text-[13px] font-medium hover:bg-[#FEF2F2] active:scale-[0.98] transition-all duration-200">
              Delete Workspace
            </button>
          </div>

        </div>
      </div>
    </div>
  )
}
