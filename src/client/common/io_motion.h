#ifndef __IO_MOTION_H
#define __IO_MOTION_H
#include "..\Util\CFileLIST.h"

#ifndef SAFE_DELETE
    #define SAFE_DELETE(p)  \
        {                   \
            if (p) {        \
                delete (p); \
                (p) = NULL; \
            }               \
        }
#endif

typedef unsigned int HNODE;
//-------------------------------------------------------------------------------------------------
struct tagMOTION {
    HNODE m_hMotion;

    WORD m_wFPS;
    WORD m_wTotalFrame;
    short* m_pFrameEvent;
    short m_nActionIdx;

    short m_nActionPointCNT;
    WORD m_wTatalAttackFrame;

    /// True when this motion carries action frame 25 -- the melee-skill hit frame,
    /// and the only frame whose handler drains the caster's queued skill payload.
    /// Mob skill motions mostly carry frame 24 instead, which ActionSkill()
    /// dispatches by SKILL_TYPE, and SKILL_ACTION_IMMEDIATE has no case there.
    /// ActionSkill() reads this flag to know whether it must drain an immediate
    /// skill itself or leave it to a real frame 25 later in the same motion.
    /// Computed once, at load.
    bool m_bHasSkillHitActionFrame;

    /// True when this motion carries action frame 24 or 34 -- the ActionSkill()
    /// frames that launch a projectile skill's bullet. A monster whose casting /
    /// skill slots were filled with idle + attack clips (Mukuroji: pig01 model) has
    /// none, so its "projectile" skill reaches the attack clip's melee frame 21
    /// instead; ActionInFighting() reads this to present that frame as the
    /// skill's impact. Computed once, at load.
    bool m_bHasProjectileFireFrame;

#ifdef __SERVER
    short* m_pActionPoint;
#else
    int m_iInterpolationInterval;
#endif

    tagMOTION();
    ~tagMOTION() { SAFE_DELETE(m_pFrameEvent); }

    bool LoadZMO(char* szFileName);

    // dwPassTIME동안 진행될 프레임수... dwPassTIME == 1000이면 1초 !!
    WORD Get_TotalFRAME() { return m_wTotalFrame; }

    WORD Get_ReaminFRAME(WORD wCurFrame) { return (m_wTotalFrame - wCurFrame); }

    WORD Get_PassFRAME(DWORD dwPassTIME, float fRatio) {
        return (WORD)((fRatio * m_wFPS * dwPassTIME) / 1000.f);
    }

    // wFrame동안 소용될 시간...
    DWORD Get_NeedTIME(WORD wFrame) { return (DWORD)((1000 * wFrame) / m_wFPS); }
    DWORD Get_NeedTIME(WORD wFrame, float fRatio) {
        return (DWORD)((1000 * wFrame) / (fRatio * m_wFPS));
    }
};

/// motion list
class CMotionLIST: public CFileLIST<tagMOTION*> {
private:
    tagMOTION* m_pTmpMotion;

    short m_nFemaleIndex;

    bool Load_FILE(tagFileDATA<tagMOTION*>* pData);
    void Free_FILE(tagFileDATA<tagMOTION*>* pData);

public:
#ifdef __SERVER
    CMotionLIST(): CFileLIST<tagMOTION*>((char*)"ANI ", 2048) { ; }
#else
    CMotionLIST(): CFileLIST<tagMOTION*>("ANI ") { ; }
#endif
    ~CMotionLIST();

    bool Load(char* szSTBFile, short nFileNameColNO = 0, char* szBaseDIR = NULL);
    void Free();

    tagMOTION* KEY_GetMOTION(unsigned int uiKEY) { return this->Get_DATAUseKEY(uiKEY); }
    tagMOTION* IDX_GetMOTION(short nIndex, bool bIsFemale);
    HNODE KEY_GetZMOTION(unsigned int uiKEY);
};
extern CMotionLIST g_MotionFILE;

//-------------------------------------------------------------------------------------------------
#endif