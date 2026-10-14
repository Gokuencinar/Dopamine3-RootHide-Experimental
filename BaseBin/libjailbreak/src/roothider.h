#ifndef ROOTHIDER_H
#define ROOTHIDER_H

#include "roothider/log.h"
#include "roothider/common.h"
#include "roothider/ptrace.h"
#include "roothider/mach_exc.h"
#include "roothider/exec_patch.h"
#include "roothider/jailbreakd.h"
#include "roothider/xpc_private.h"
// The crash reporter is owned by launchdhook, not the public RootHide API.
// Its legacy donor header conflicts with Dopamine 3's crashreporter.h ABI.

extern int roothide_unsupport_request();
extern bool roothide_domain_allowed(audit_token_t clientToken);

#endif // ROOTHIDER_H
