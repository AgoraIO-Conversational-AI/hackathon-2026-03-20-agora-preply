# ruff: noqa: E501
"""Explore Classtime SchoolAdmin API - test token and account operations.

Usage:
  uv run python manage.py explore_admin_token
  uv run python manage.py explore_admin_token --step 1
  uv run python manage.py explore_admin_token --admin-token "eyJ..."
"""

import contextlib
import json
import os

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand

PROTO_BASE = "https://www.classtime.com/service/public"
SCHOOL_ID = "3WoUh63lsg3UaOrCfQYeOt"  # from JWT sid claim


def _proto_call(service: str, method: str, body: dict, token: str) -> dict:
    url = f"{PROTO_BASE}/{service}/{method}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json,*/*",
        "Authorization": f"JWT {token}",
    }
    resp = httpx.post(url, json=body, headers=headers, timeout=30)
    return resp.json()


def _fmt(data: dict) -> str:
    return json.dumps(data, indent=2, default=str)


class Command(BaseCommand):
    help = "Explore Classtime SchoolAdmin API"

    def add_arguments(self, parser):
        parser.add_argument("--step", type=int, help="Run only step N (1-11)")
        parser.add_argument("--admin-token", help="Override admin token")

    def handle(self, *args, **options):
        token = (
            options.get("admin_token")
            or os.environ.get("CLASSTIME_ADMIN_TOKEN")
            or getattr(settings, "CLASSTIME_ADMIN_TOKEN", "")
        )
        if not token:
            self.stderr.write(self.style.ERROR("No admin token. Set CLASSTIME_ADMIN_TOKEN or use --admin-token"))
            return

        step_filter = options.get("step")
        ctx = {}  # shared context between steps

        # Allow running a range: --step 40 runs 40-48
        step_range = None
        if step_filter and step_filter >= 40:
            step_range = range(step_filter, 49)

        steps = [
            (1, "Verify admin token", self._step_1_verify_admin),
            (2, "Create teacher account (getOrCreateExternalAccount)", self._step_2_create_teacher),
            (3, "Associate teacher with school", self._step_3_associate_teacher),
            (4, "Mint teacher token", self._step_4_mint_teacher_token),
            (5, "Verify minted teacher token", self._step_5_verify_teacher_token),
            (6, "Create student account (getOrCreateExternalAccount)", self._step_6_create_student),
            (7, "Associate student with school (test)", self._step_7_associate_student),
            (8, "Mint student token", self._step_8_mint_student_token),
            (9, "Verify minted student token", self._step_9_verify_student_token),
            (10, "Idempotency check (re-create teacher)", self._step_10_idempotency),
            (11, "Alternative: createAccount", self._step_11_create_account),
            (12, "Get existing teacher info via current token", self._step_12_get_existing_teacher),
            (13, "Associate existing teacher with school", self._step_13_associate_existing),
            (14, "Mint token for existing teacher", self._step_14_mint_existing),
            (15, "Verify new token for existing teacher", self._step_15_verify_existing),
            (16, "Mint token for admin (self)", self._step_16_mint_admin_self),
            (17, "Lookup by email (getAccountIdByEmail)", self._step_17_lookup_email),
            (18, "Explore organization structure", self._step_18_explore_org),
            (19, "Associate admin with org", self._step_19_associate_member),
            (20, "Retry mint token after org", self._step_20_retry_mint_after_org),
            (21, "School/associateTeacher for admin", self._step_21_school_associate_admin),
            (22, "updateOrganizationMembers (add admin)", self._step_22_update_org_members),
            (23, "Retry mint after school association", self._step_23_retry_mint),
            (24, "updateOrganization (add members)", self._step_24_update_org),
            (25, "Retry mint after updateOrganization", self._step_25_final_mint),
            (26, "Get private account data", self._step_26_private_data),
            (27, "getOrCreateExternalAccount with organisation field", self._step_27_gocea_with_org),
            (28, "Try REST API account endpoints", self._step_28_rest_api),
            (29, "Create fresh teacher via web-signup simulation", self._step_29_fresh_account),
            (30, "getAccountProfile for admin", self._step_30_get_profile),
            (31, "Admin token as teacher (Proto operations)", self._step_31_admin_as_teacher),
            (32, "Admin token for REST API (question sets)", self._step_32_admin_rest),
            (33, "Try createToken for admin with TEACHER scope", self._step_33_teacher_scoped_token),
            (34, "SchoolAdmin dashboard REST endpoints", self._step_34_admin_dashboard),
            (35, "createToken with permission field", self._step_35_token_with_permission),
            (40, "Micha's flow: getOrCreateAccount (teacher)", self._step_40_micha_create_teacher),
            (41, "Micha's flow: associateMember (teacher to org)", self._step_41_micha_associate),
            (42, "Micha's flow: createToken (teacher)", self._step_42_micha_teacher_token),
            (43, "Verify minted teacher token", self._step_43_verify_teacher),
            (44, "Micha's flow: getOrCreateAccount (student)", self._step_44_micha_create_student),
            (45, "Micha's flow: createToken (student)", self._step_45_micha_student_token),
            (46, "Verify minted student token", self._step_46_verify_student),
            (47, "Idempotency: re-create same teacher", self._step_47_idempotency),
            (48, "Create teacher with existing email (admin)", self._step_48_existing_email),
        ]

        for num, desc, fn in steps:
            if step_range and num not in step_range:
                continue
            if step_filter and not step_range and num != step_filter:
                continue
            self.stdout.write(f"\n{'=' * 60}")
            self.stdout.write(self.style.HTTP_INFO(f"Step {num}: {desc}"))
            self.stdout.write(f"{'=' * 60}")
            try:
                fn(token, ctx)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Exception: {e}"))

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(self.style.SUCCESS("Done. Context:"))
        self.stdout.write(_fmt(ctx))

    def _call(self, service: str, method: str, body: dict, token: str) -> dict:
        self.stdout.write(f"  POST {service}/{method}")
        self.stdout.write(f"  Body: {_fmt(body)}")
        result = _proto_call(service, method, body, token)
        self.stdout.write(f"  Response: {_fmt(result)}")
        if "classtimeErrorCode" in result:
            self.stdout.write(self.style.WARNING(f"  Error: {result.get('message', 'unknown')}"))
        return result

    # --- Steps ---

    def _step_1_verify_admin(self, token: str, ctx: dict):
        result = self._call("Account", "getMyAccountInfo", {}, token)
        ctx["admin_classtime_id"] = result.get("classtimeId")
        ctx["admin_role"] = result.get("role")
        ctx["admin_orgs"] = result.get("organizations")
        if result.get("classtimeId"):
            self.stdout.write(
                self.style.SUCCESS(f"  Admin account: {result['classtimeId']}, role: {result.get('role')}")
            )

    def _step_2_create_teacher(self, token: str, ctx: dict):
        body = {
            "role": "TEACHER",
            "userProfile": {"firstName": "Test", "lastName": "PreplyTeacher"},
            "subject": "preply-test-teacher-001",
            "email": "test-teacher-001@preply-hackathon.example",
        }
        result = self._call("Account", "getOrCreateExternalAccount", body, token)
        teacher_id = result.get("accountId") or result.get("account_id")
        ctx["test_teacher_id"] = teacher_id
        if teacher_id:
            self.stdout.write(self.style.SUCCESS(f"  Teacher account ID: {teacher_id}"))
        else:
            # Try snake_case as fallback
            self.stdout.write("  Trying snake_case fields...")
            body_snake = {
                "role": "TEACHER",
                "user_profile": {"first_name": "Test", "last_name": "PreplyTeacher"},
                "subject": "preply-test-teacher-001",
                "email": "test-teacher-001@preply-hackathon.example",
            }
            result = self._call("Account", "getOrCreateExternalAccount", body_snake, token)
            teacher_id = result.get("accountId") or result.get("account_id")
            ctx["test_teacher_id"] = teacher_id
            if teacher_id:
                self.stdout.write(self.style.SUCCESS(f"  Teacher account ID (snake_case): {teacher_id}"))

    def _step_3_associate_teacher(self, token: str, ctx: dict):
        teacher_id = ctx.get("test_teacher_id")
        if not teacher_id:
            self.stdout.write(self.style.WARNING("  Skipping - no teacher ID from step 2"))
            return
        body = {"schoolId": SCHOOL_ID, "accountId": teacher_id}
        result = self._call("School", "associateTeacher", body, token)
        ctx["teacher_associated"] = "classtimeErrorCode" not in result
        if ctx["teacher_associated"]:
            self.stdout.write(self.style.SUCCESS("  Teacher associated with school"))

    def _step_4_mint_teacher_token(self, token: str, ctx: dict):
        teacher_id = ctx.get("test_teacher_id")
        if not teacher_id:
            self.stdout.write(self.style.WARNING("  Skipping - no teacher ID"))
            return
        body = {"classtimeId": teacher_id}
        result = self._call("Account", "createToken", body, token)
        ctx["test_teacher_token"] = result.get("token")
        ctx["test_teacher_token_valid_until"] = result.get("validUntil")
        if result.get("token"):
            self.stdout.write(self.style.SUCCESS(f"  Teacher token minted, valid until: {result.get('validUntil')}"))

    def _step_5_verify_teacher_token(self, token: str, ctx: dict):
        teacher_token = ctx.get("test_teacher_token")
        if not teacher_token:
            self.stdout.write(self.style.WARNING("  Skipping - no teacher token"))
            return
        # Verify with getMyAccountInfo
        result = self._call("Account", "getMyAccountInfo", {}, teacher_token)
        ctx["teacher_verified_role"] = result.get("role")
        if result.get("classtimeId"):
            self.stdout.write(self.style.SUCCESS(f"  Verified: {result['classtimeId']}, role: {result.get('role')}"))
        # Also test if it can list sessions
        self.stdout.write("  Testing Session/getSessions with teacher token...")
        result2 = self._call("Session", "getSessions", {}, teacher_token)
        ctx["teacher_can_list_sessions"] = "classtimeErrorCode" not in result2
        session_count = len(result2.get("sessions", []))
        self.stdout.write(f"  Sessions visible: {session_count}")

    def _step_6_create_student(self, token: str, ctx: dict):
        body = {
            "role": "STUDENT",
            "userProfile": {"firstName": "Test", "lastName": "PreplyStudent"},
            "subject": "preply-test-student-001",
            "email": "test-student-001@preply-hackathon.example",
        }
        result = self._call("Account", "getOrCreateExternalAccount", body, token)
        student_id = result.get("accountId") or result.get("account_id")
        ctx["test_student_id"] = student_id
        if student_id:
            self.stdout.write(self.style.SUCCESS(f"  Student account ID: {student_id}"))
        elif not result.get("classtimeErrorCode"):
            # Try snake_case
            self.stdout.write("  Trying snake_case fields...")
            body_snake = {
                "role": "STUDENT",
                "user_profile": {"first_name": "Test", "last_name": "PreplyStudent"},
                "subject": "preply-test-student-001",
                "email": "test-student-001@preply-hackathon.example",
            }
            result = self._call("Account", "getOrCreateExternalAccount", body_snake, token)
            student_id = result.get("accountId") or result.get("account_id")
            ctx["test_student_id"] = student_id

    def _step_7_associate_student(self, token: str, ctx: dict):
        student_id = ctx.get("test_student_id")
        if not student_id:
            self.stdout.write(self.style.WARNING("  Skipping - no student ID from step 6"))
            return
        body = {"schoolId": SCHOOL_ID, "accountId": student_id}
        result = self._call("School", "associateTeacher", body, token)
        ctx["student_associated"] = "classtimeErrorCode" not in result
        if ctx["student_associated"]:
            self.stdout.write(self.style.SUCCESS("  Student associated with school (unexpected but works!)"))
        else:
            self.stdout.write("  Student association failed (expected - associateTeacher is for teachers)")

    def _step_8_mint_student_token(self, token: str, ctx: dict):
        student_id = ctx.get("test_student_id")
        if not student_id:
            self.stdout.write(self.style.WARNING("  Skipping - no student ID"))
            return
        body = {"classtimeId": student_id}
        result = self._call("Account", "createToken", body, token)
        ctx["test_student_token"] = result.get("token")
        ctx["test_student_token_valid_until"] = result.get("validUntil")
        if result.get("token"):
            self.stdout.write(self.style.SUCCESS(f"  Student token minted, valid until: {result.get('validUntil')}"))

    def _step_9_verify_student_token(self, token: str, ctx: dict):
        student_token = ctx.get("test_student_token")
        if not student_token:
            self.stdout.write(self.style.WARNING("  Skipping - no student token"))
            return
        result = self._call("Account", "getMyAccountInfo", {}, student_token)
        ctx["student_verified_role"] = result.get("role")
        if result.get("classtimeId"):
            self.stdout.write(self.style.SUCCESS(f"  Verified: {result['classtimeId']}, role: {result.get('role')}"))

    def _step_10_idempotency(self, token: str, ctx: dict):
        body = {
            "role": "TEACHER",
            "userProfile": {"firstName": "Test", "lastName": "PreplyTeacher"},
            "subject": "preply-test-teacher-001",
            "email": "test-teacher-001@preply-hackathon.example",
        }
        result = self._call("Account", "getOrCreateExternalAccount", body, token)
        new_id = result.get("accountId") or result.get("account_id")
        original_id = ctx.get("test_teacher_id")
        ctx["idempotent"] = new_id == original_id
        if new_id == original_id:
            self.stdout.write(self.style.SUCCESS(f"  Idempotent! Same ID: {new_id}"))
        else:
            self.stdout.write(self.style.WARNING(f"  NOT idempotent! Original: {original_id}, New: {new_id}"))

    def _step_11_create_account(self, token: str, ctx: dict):
        # Try multiple formats for createAccount

        # Format A: Micha's organization.md format (flat, camelCase)
        self.stdout.write("  --- Format A: Micha's flat format ---")
        body_a = {
            "role": "Teacher",
            "subject": "preply-test-alt-001",
            "userProfile": {"firstName": "Alt", "lastName": "MethodA"},
        }
        result_a = self._call("Account", "createAccount", body_a, token)
        alt_id = result_a.get("accountId") or result_a.get("account_id")
        if alt_id:
            ctx["alt_teacher_id"] = alt_id
            self.stdout.write(self.style.SUCCESS(f"  Format A worked! Account: {alt_id}"))
            return

        # Format B: Wrapped in "account" field per proto CreateAccountRequest
        self.stdout.write("  --- Format B: proto-style wrapped in 'account' ---")
        body_b = {
            "account": {
                "userProfile": {"firstName": "Alt", "lastName": "MethodB"},
                "roles": ["TEACHER"],
                "authenticationMethods": [
                    {
                        "provider": "EXTERNAL",
                        "email": "alt-method-b@preply-hackathon.example",
                        "subject": "preply-test-alt-002",
                    }
                ],
            }
        }
        result_b = self._call("Account", "createAccount", body_b, token)
        alt_id = result_b.get("accountId") or result_b.get("account_id")
        if alt_id:
            ctx["alt_teacher_id"] = alt_id
            self.stdout.write(self.style.SUCCESS(f"  Format B worked! Account: {alt_id}"))
            return

        # Format C: createExternalAccount instead
        self.stdout.write("  --- Format C: createExternalAccount ---")
        body_c = {
            "role": "TEACHER",
            "userProfile": {"firstName": "Alt", "lastName": "MethodC"},
            "subject": "preply-test-alt-003",
            "email": "alt-method-c@preply-hackathon.example",
        }
        result_c = self._call("Account", "createExternalAccount", body_c, token)
        alt_id = result_c.get("accountId") or result_c.get("account_id")
        if alt_id:
            ctx["alt_teacher_id"] = alt_id
            self.stdout.write(self.style.SUCCESS(f"  Format C (createExternalAccount) worked! Account: {alt_id}"))
            return

        # Format D: getOrCreateAccounts (batch, marked public_api in proto)
        self.stdout.write("  --- Format D: getOrCreateAccounts (batch) ---")
        body_d = {
            "accountsDetails": [
                {
                    "email": "alt-method-d@preply-hackathon.example",
                    "role": "TEACHER",
                    "provider": "EXTERNAL",
                    "subject": "preply-test-alt-004",
                    "firstName": "Alt",
                    "lastName": "MethodD",
                }
            ]
        }
        result_d = self._call("Account", "getOrCreateAccounts", body_d, token)
        infos = result_d.get("accountInfos") or result_d.get("account_infos") or {}
        if infos:
            for email, info in infos.items():
                alt_id = info.get("accountId") or info.get("account_id")
                ctx["alt_teacher_id"] = alt_id
                self.stdout.write(self.style.SUCCESS(f"  Format D (batch) worked! {email} -> {alt_id}"))
            return

        self.stdout.write(self.style.WARNING("  All createAccount formats failed"))

    def _step_12_get_existing_teacher(self, token: str, ctx: dict):
        """Use the CLASSTIME_TEACHER_TOKEN to identify the existing teacher account."""
        teacher_token = getattr(settings, "CLASSTIME_TEACHER_TOKEN", "") or os.environ.get(
            "CLASSTIME_TEACHER_TOKEN", ""
        )
        if not teacher_token:
            self.stdout.write(self.style.WARNING("  No CLASSTIME_TEACHER_TOKEN set, skipping"))
            return
        result = self._call("Account", "getMyAccountInfo", {}, teacher_token)
        existing_id = result.get("classtimeId")
        ctx["existing_teacher_id"] = existing_id
        ctx["existing_teacher_role"] = result.get("role")
        ctx["existing_teacher_orgs"] = result.get("organizations")
        if existing_id:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Existing teacher: {existing_id}, role: {result.get('role')}, orgs: {result.get('organizations')}"
                )
            )

    def _step_13_associate_existing(self, token: str, ctx: dict):
        """Associate the existing teacher with the Preply school."""
        teacher_id = ctx.get("existing_teacher_id")
        if not teacher_id:
            self.stdout.write(self.style.WARNING("  Skipping - no existing teacher ID"))
            return
        body = {"schoolId": SCHOOL_ID, "accountId": teacher_id}
        result = self._call("School", "associateTeacher", body, token)
        ctx["existing_teacher_associated"] = "classtimeErrorCode" not in result
        if ctx["existing_teacher_associated"]:
            self.stdout.write(self.style.SUCCESS("  Existing teacher associated with Preply school!"))

    def _step_14_mint_existing(self, token: str, ctx: dict):
        """Mint a new token for the existing teacher via admin token."""
        teacher_id = ctx.get("existing_teacher_id")
        if not teacher_id:
            self.stdout.write(self.style.WARNING("  Skipping - no existing teacher ID"))
            return
        body = {"classtimeId": teacher_id}
        result = self._call("Account", "createToken", body, token)
        ctx["existing_teacher_new_token"] = result.get("token")
        ctx["existing_teacher_new_valid"] = result.get("validUntil")
        if result.get("token"):
            self.stdout.write(self.style.SUCCESS(f"  New token minted! Valid until: {result.get('validUntil')}"))
            self.stdout.write(f"  Token: {result['token'][:50]}...")

    def _step_15_verify_existing(self, token: str, ctx: dict):
        """Verify the newly minted token works for the existing teacher."""
        new_token = ctx.get("existing_teacher_new_token")
        if not new_token:
            self.stdout.write(self.style.WARNING("  Skipping - no new token"))
            return
        result = self._call("Account", "getMyAccountInfo", {}, new_token)
        if result.get("classtimeId"):
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Verified: {result['classtimeId']}, role: {result.get('role')}, orgs: {result.get('organizations')}"
                )
            )
        # Test listing sessions
        self.stdout.write("  Testing Session/getSessions with new token...")
        result2 = self._call("Session", "getSessions", {}, new_token)
        has_sessions = "classtimeErrorCode" not in result2
        session_count = len(result2.get("sessions", []))
        self.stdout.write(f"  Can list sessions: {has_sessions}, count: {session_count}")

    def _step_16_mint_admin_self(self, token: str, ctx: dict):
        """Mint a token for the admin's own account (test createToken works)."""
        admin_id = ctx.get("admin_classtime_id") or "v6b9rJEQL2IqrTXkJ_YyvQ"
        body = {"classtimeId": admin_id}
        result = self._call("Account", "createToken", body, token)
        if result.get("token"):
            ctx["admin_new_token"] = result.get("token")
            self.stdout.write(self.style.SUCCESS(f"  Admin self-token minted! Valid until: {result.get('validUntil')}"))
        else:
            self.stdout.write("  Trying with role...")
            body2 = {"classtimeId": admin_id, "role": "TEACHER"}
            result2 = self._call("Account", "createToken", body2, token)
            if result2.get("token"):
                ctx["admin_as_teacher_token"] = result2.get("token")
                self.stdout.write(self.style.SUCCESS("  Admin-as-teacher token minted!"))

    def _step_17_lookup_email(self, token: str, ctx: dict):
        """Look up an account by email."""
        body = {"email": "vasyl.stanislavchuk@gmail.com", "role": "TEACHER"}
        result = self._call("Account", "getAccountIdByEmail", body, token)
        looked_up_id = result.get("accountId") or result.get("account_id")
        if looked_up_id:
            ctx["looked_up_id"] = looked_up_id
            self.stdout.write(self.style.SUCCESS(f"  Found account by email: {looked_up_id}"))
        # Also try with SchoolAdmin role
        body2 = {"email": "vasyl.stanislavchuk@gmail.com", "role": "SchoolAdmin"}
        result2 = self._call("Account", "getAccountIdByEmail", body2, token)
        looked_up_id2 = result2.get("accountId") or result2.get("account_id")
        if looked_up_id2:
            self.stdout.write(self.style.SUCCESS(f"  Found SchoolAdmin by email: {looked_up_id2}"))

    def _step_21_school_associate_admin(self, token: str, ctx: dict):
        """Associate admin's own account with the Preply school (not org)."""
        admin_id = "v6b9rJEQL2IqrTXkJ_YyvQ"
        body = {"schoolId": SCHOOL_ID, "accountId": admin_id}
        result = self._call("School", "associateTeacher", body, token)
        ctx["admin_school_associated"] = "classtimeErrorCode" not in result
        if ctx["admin_school_associated"]:
            self.stdout.write(self.style.SUCCESS("  Admin associated with school via School/associateTeacher!"))

    def _step_22_update_org_members(self, token: str, ctx: dict):
        """Try updateOrganizationMembers to add admin to org."""
        org_id = "b47a32f4-8656-4c8f-9c5c-92e8a69c1d37"
        admin_id = "v6b9rJEQL2IqrTXkJ_YyvQ"
        body = {
            "organizationId": org_id,
            "organizationMemberUpdates": [
                {
                    "memberAdded": {
                        "accountId": admin_id,
                        "isAdmin": True,
                    }
                }
            ],
        }
        result = self._call("Account", "updateOrganizationMembers", body, token)
        ctx["admin_org_updated"] = "classtimeErrorCode" not in result
        if ctx["admin_org_updated"]:
            self.stdout.write(self.style.SUCCESS("  Admin added to org via updateOrganizationMembers!"))

    def _step_23_retry_mint(self, token: str, ctx: dict):
        """Retry createToken after school/org association."""
        admin_id = "v6b9rJEQL2IqrTXkJ_YyvQ"
        body = {"classtimeId": admin_id}
        result = self._call("Account", "createToken", body, token)
        if result.get("token"):
            ctx["admin_new_token"] = result["token"]
            self.stdout.write(self.style.SUCCESS(f"  Token minted! Valid: {result.get('validUntil')}"))
            self.stdout.write(f"  Token: {result['token'][:80]}...")

    def _step_26_private_data(self, token: str, ctx: dict):
        """Get the raw account entity to see what fields are actually stored."""
        admin_id = "v6b9rJEQL2IqrTXkJ_YyvQ"
        result = self._call("Account", "getPrivateAccountData", {"accountId": admin_id}, token)
        account = result.get("account", {})
        if account:
            self.stdout.write(f"  Account entity: {_fmt(account)}")
        # Also try getAccountProfile
        result2 = self._call("Account", "getAccountProfile", {"accountId": admin_id}, token)
        if result2.get("accountProfile"):
            self.stdout.write(f"  Profile: {_fmt(result2['accountProfile'])}")

    def _step_27_gocea_with_org(self, token: str, ctx: dict):
        """Try getOrCreateExternalAccount with extra organisation field."""
        # The CreateExternalAccountRequest has an 'organisation' field (field 5)
        # Maybe getOrCreateExternalAccount also accepts it even if not in proto
        body = {
            "role": "TEACHER",
            "userProfile": {"firstName": "Test", "lastName": "PreplyOrg"},
            "subject": "preply-test-org-001",
            "email": "test-org-001@preply-hackathon.example",
            "organisation": "preply",
        }
        result = self._call("Account", "getOrCreateExternalAccount", body, token)
        acct_id = result.get("accountId") or result.get("account_id")
        if acct_id:
            ctx["org_teacher_id"] = acct_id
            self.stdout.write(self.style.SUCCESS(f"  Created with org field! ID: {acct_id}"))

    def _step_28_rest_api(self, token: str, ctx: dict):
        """Try REST API endpoints for account management."""
        import httpx as _httpx

        rest_base = "https://api.classtime.com/teachers-api/v2"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://www.classtime.com",
            "Referer": "https://www.classtime.com/",
            "Cookie": f"service-jwt-0={token}",
        }

        # Try listing school members or any account-related REST endpoints
        self.stdout.write("  --- REST: GET schools/ ---")
        resp = _httpx.get(f"{rest_base}/schools/", headers=headers, timeout=30)
        self.stdout.write(f"  Status: {resp.status_code}")
        try:
            self.stdout.write(f"  Response: {_fmt(resp.json())}")
        except Exception:
            self.stdout.write(f"  Raw: {resp.text[:500]}")

        self.stdout.write("  --- REST: GET accounts/ ---")
        resp2 = _httpx.get(f"{rest_base}/accounts/", headers=headers, timeout=30)
        self.stdout.write(f"  Status: {resp2.status_code}")
        try:
            self.stdout.write(f"  Response: {_fmt(resp2.json())}")
        except Exception:
            self.stdout.write(f"  Raw: {resp2.text[:500]}")

        self.stdout.write("  --- REST: GET users/ ---")
        resp3 = _httpx.get(f"{rest_base}/users/", headers=headers, timeout=30)
        self.stdout.write(f"  Status: {resp3.status_code}")
        try:
            self.stdout.write(f"  Response: {_fmt(resp3.json())}")
        except Exception:
            self.stdout.write(f"  Raw: {resp3.text[:500]}")

        # Try the school-admin specific REST base
        self.stdout.write("  --- REST: GET school-admin/ (alternative base) ---")
        resp4 = _httpx.get("https://api.classtime.com/school-admin-api/v1/schools/", headers=headers, timeout=30)
        self.stdout.write(f"  Status: {resp4.status_code}")
        try:
            self.stdout.write(f"  Response: {_fmt(resp4.json())}")
        except Exception:
            self.stdout.write(f"  Raw: {resp4.text[:500]}")

    def _step_29_fresh_account(self, token: str, ctx: dict):
        """Try Account/login to simulate creating a new teacher via EXTERNAL provider."""
        # Login with EXTERNAL provider and a unique subject
        body = {
            "provider": "EXTERNAL",
            "role": "TEACHER",
            "successRedirectUrl": "https://www.classtime.com/",
        }
        result = self._call("Account", "login", body, token)
        if result.get("redirectUrl"):
            self.stdout.write(f"  Login redirect: {result['redirectUrl']}")
        # Try authorization with nickname
        body2 = {
            "loginState": result.get("loginState", {}),
            "nickname": "PreplyTestTeacher",
        }
        if result.get("loginState"):
            result2 = self._call("Account", "authorization", body2, token)
            self.stdout.write(f"  Auth result: {_fmt(result2)}")

    def _step_30_get_profile(self, token: str, ctx: dict):
        """Get account profiles for known IDs."""
        admin_id = "v6b9rJEQL2IqrTXkJ_YyvQ"
        result = self._call("Account", "getAccountProfiles", {"accountIds": [admin_id]}, token)
        profiles = result.get("accountProfiles", {})
        for acct_id, profile in profiles.items():
            self.stdout.write(f"  {acct_id}: {_fmt(profile)}")

    def _step_31_admin_as_teacher(self, token: str, ctx: dict):
        """Test if admin token can do teacher Proto operations."""
        # List sessions
        self.stdout.write("  --- Session/getSessions ---")
        result = self._call("Session", "getSessions", {}, token)
        has_sessions = "classtimeErrorCode" not in result
        session_count = len(result.get("sessions", []))
        self.stdout.write(f"  Can list sessions: {has_sessions}, count: {session_count}")

        # Create a test question set via Proto API
        self.stdout.write("  --- Library/createQuestionSet ---")
        result2 = self._call("Library", "createQuestionSet", {"title": "Admin Token Test"}, token)
        qs_info = result2.get("questionSetInfo", {})
        qs_id = qs_info.get("id")
        if qs_id:
            ctx["admin_qs_id"] = qs_id
            self.stdout.write(self.style.SUCCESS(f"  Created question set: {qs_id}"))
        else:
            self.stdout.write(f"  Result: {_fmt(result2)}")

    def _step_32_admin_rest(self, token: str, ctx: dict):
        """Test if admin token works for REST API with JWT header instead of cookie."""
        import httpx as _httpx

        rest_base = "https://api.classtime.com/teachers-api/v2"

        # Try with JWT Authorization header instead of cookie
        headers_jwt = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://www.classtime.com",
            "Referer": "https://www.classtime.com/",
            "Authorization": f"JWT {token}",
        }

        self.stdout.write("  --- REST with Authorization header: GET question-sets/ ---")
        resp = _httpx.get(f"{rest_base}/question-sets/", headers=headers_jwt, timeout=30)
        self.stdout.write(f"  Status: {resp.status_code}")
        try:
            data = resp.json()
            if isinstance(data, list):
                self.stdout.write(f"  Question sets: {len(data)} found")
            else:
                self.stdout.write(f"  Response: {_fmt(data)}")
        except Exception:
            self.stdout.write(f"  Raw: {resp.text[:300]}")

        # Try with cookie auth
        headers_cookie = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://www.classtime.com",
            "Referer": "https://www.classtime.com/",
            "Cookie": f"service-jwt-0={token}",
        }

        self.stdout.write("  --- REST with Cookie: GET question-sets/ ---")
        resp2 = _httpx.get(f"{rest_base}/question-sets/", headers=headers_cookie, timeout=30)
        self.stdout.write(f"  Status: {resp2.status_code}")
        try:
            data2 = resp2.json()
            if isinstance(data2, list):
                self.stdout.write(f"  Question sets: {len(data2)} found")
                if data2:
                    self.stdout.write(f"  First QS: {data2[0].get('id')} - {data2[0].get('title')}")
            else:
                self.stdout.write(f"  Response: {_fmt(data2)}")
        except Exception:
            self.stdout.write(f"  Raw: {resp2.text[:300]}")

    def _step_33_teacher_scoped_token(self, token: str, ctx: dict):
        """Create a TEACHER-scoped token for the admin account using refreshToken."""
        # Try refreshToken - maybe it returns a teacher-scoped token
        self.stdout.write("  --- Account/refreshToken ---")
        result = self._call("Account", "refreshToken", {}, token)
        if result.get("headerToken"):
            new_token = result["headerToken"]
            ctx["refreshed_token"] = new_token
            self.stdout.write(self.style.SUCCESS(f"  Got refreshed token! {new_token[:50]}..."))
            # Check what role it has
            result2 = self._call("Account", "getMyAccountInfo", {}, new_token)
            self.stdout.write(f"  Refreshed token role: {result2.get('role')}")
        else:
            self.stdout.write(f"  Result: {_fmt(result)}")

    def _step_34_admin_dashboard(self, token: str, ctx: dict):
        """Test SchoolAdmin-specific REST or dashboard endpoints."""
        import httpx as _httpx

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cookie": f"service-jwt-0={token}",
        }

        # Try various school-admin endpoints
        urls = [
            "https://www.classtime.com/api/school-admin/teachers",
            "https://www.classtime.com/api/school-admin/members",
            "https://www.classtime.com/api/admin/members",
            "https://api.classtime.com/admin-api/v1/members/",
        ]
        for url in urls:
            self.stdout.write(f"  --- GET {url} ---")
            resp = _httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
            self.stdout.write(f"  Status: {resp.status_code}")
            with contextlib.suppress(Exception):
                self.stdout.write(f"  Response: {resp.text[:300]}")

        # Also try SchoolAdmin proto service methods we haven't discovered
        self.stdout.write("  --- SchoolAdmin/getSchool ---")
        self._call("SchoolAdmin", "getSchool", {"schoolId": SCHOOL_ID}, token)
        self.stdout.write("  (any result is good)")

        self.stdout.write("  --- School/getSchool ---")
        self._call("School", "getSchool", {"schoolId": SCHOOL_ID}, token)
        self.stdout.write("  (any result)")

        # Try listing all methods on Account
        self.stdout.write("  --- Account/getOrganization with detailed flag ---")
        org_id = "b47a32f4-8656-4c8f-9c5c-92e8a69c1d37"
        result3 = self._call(
            "Account",
            "getOrganization",
            {
                "organizationId": org_id,
                "shouldIncludeAllMembers": True,
            },
            token,
        )
        members = result3.get("organizationMembers", [])
        for m in members:
            acct_ref = m.get("accountRef", {})
            self.stdout.write(f"  Member: {acct_ref.get('id')}, admin: {m.get('isAdmin')}, added: {m.get('addedAt')}")

    def _step_35_token_with_permission(self, token: str, ctx: dict):
        """Try createToken with permission field variations."""
        admin_id = "v6b9rJEQL2IqrTXkJ_YyvQ"

        # Try various permission values
        permissions = [
            "Teacher",
            "Teacher/",
            "",
            "SchoolAdmin",
            "SchoolAdmin/",
        ]
        for perm in permissions:
            body = {"classtimeId": admin_id, "permission": perm} if perm else {"classtimeId": admin_id}
            if perm:
                body["role"] = "TEACHER"
            self.stdout.write(f"  --- permission='{perm}' ---")
            result = self._call("Account", "createToken", body, token)
            if result.get("token"):
                ctx[f"token_perm_{perm}"] = result["token"]
                self.stdout.write(self.style.SUCCESS(f"  GOT TOKEN with permission={perm}!"))
                break

    # === Micha's corrected flow (steps 40-48) ===

    def _step_40_micha_create_teacher(self, token: str, ctx: dict):
        """getOrCreateAccount (NOT getOrCreateExternalAccount!) with snake_case."""
        body = {
            "role": "TEACHER",
            "user_profile": {
                "first_name": "Test",
                "last_name": "PreplyTeacher",
            },
            "subject": "preply-test-teacher-001",
            "email": "test-teacher-001@preply-hackathon.example",
        }
        result = self._call("Account", "getOrCreateAccount", body, token)
        teacher_id = result.get("account_id") or result.get("accountId")
        ctx["m_teacher_id"] = teacher_id
        if teacher_id:
            self.stdout.write(self.style.SUCCESS(f"  Teacher created! ID: {teacher_id}"))

    def _step_41_micha_associate(self, token: str, ctx: dict):
        """associateMember with snake_case org_id and account_id."""
        teacher_id = ctx.get("m_teacher_id")
        if not teacher_id:
            self.stdout.write(self.style.WARNING("  Skipping - no teacher ID"))
            return
        org_id = "b47a32f4-8656-4c8f-9c5c-92e8a69c1d37"
        body = {
            "organization_id": org_id,
            "account_id": teacher_id,
        }
        result = self._call("Account", "associateMember", body, token)
        ctx["m_teacher_associated"] = "classtimeErrorCode" not in result
        if ctx["m_teacher_associated"]:
            self.stdout.write(self.style.SUCCESS("  Teacher associated with Preply org!"))

    def _step_42_micha_teacher_token(self, token: str, ctx: dict):
        """createToken for the created teacher."""
        teacher_id = ctx.get("m_teacher_id")
        if not teacher_id:
            self.stdout.write(self.style.WARNING("  Skipping - no teacher ID"))
            return
        # Try snake_case first (matching Micha's pattern)
        body = {"classtime_id": teacher_id}
        result = self._call("Account", "createToken", body, token)
        tk = result.get("token")
        if not tk:
            # Try camelCase
            body2 = {"classtimeId": teacher_id}
            result = self._call("Account", "createToken", body2, token)
            tk = result.get("token")
        ctx["m_teacher_token"] = tk
        ctx["m_teacher_valid"] = result.get("valid_until") or result.get("validUntil")
        if tk:
            self.stdout.write(self.style.SUCCESS(f"  Teacher token minted! Valid: {ctx['m_teacher_valid']}"))
            self.stdout.write(f"  Token: {tk[:80]}...")

    def _step_43_verify_teacher(self, token: str, ctx: dict):
        """Verify the teacher token works for teacher operations."""
        tk = ctx.get("m_teacher_token")
        if not tk:
            self.stdout.write(self.style.WARNING("  Skipping - no teacher token"))
            return
        # Account info
        result = self._call("Account", "getMyAccountInfo", {}, tk)
        self.stdout.write(f"  Role: {result.get('role')}, Orgs: {result.get('organizations')}")
        # List sessions
        result2 = self._call("Session", "getSessions", {}, tk)
        has = "classtimeErrorCode" not in result2
        self.stdout.write(f"  Can list sessions: {has}")
        # Create question set
        result3 = self._call("Library", "createQuestionSet", {"title": "Token Test QS"}, tk)
        qs_id = result3.get("questionSetInfo", {}).get("id")
        if qs_id:
            ctx["m_test_qs"] = qs_id
            self.stdout.write(self.style.SUCCESS(f"  Created question set: {qs_id}"))
        else:
            self.stdout.write(f"  QS result: {_fmt(result3)}")

    def _step_44_micha_create_student(self, token: str, ctx: dict):
        """getOrCreateAccount for a student (no school association needed per Micha)."""
        body = {
            "role": "STUDENT",
            "user_profile": {
                "first_name": "Test",
                "last_name": "PreplyStudent",
            },
            "subject": "preply-test-student-001",
            "email": "test-student-001@preply-hackathon.example",
        }
        result = self._call("Account", "getOrCreateAccount", body, token)
        student_id = result.get("account_id") or result.get("accountId")
        ctx["m_student_id"] = student_id
        if student_id:
            self.stdout.write(self.style.SUCCESS(f"  Student created! ID: {student_id}"))

    def _step_45_micha_student_token(self, token: str, ctx: dict):
        """createToken for student."""
        student_id = ctx.get("m_student_id")
        if not student_id:
            self.stdout.write(self.style.WARNING("  Skipping - no student ID"))
            return
        body = {"classtime_id": student_id}
        result = self._call("Account", "createToken", body, token)
        tk = result.get("token")
        if not tk:
            body2 = {"classtimeId": student_id}
            result = self._call("Account", "createToken", body2, token)
            tk = result.get("token")
        ctx["m_student_token"] = tk
        ctx["m_student_valid"] = result.get("valid_until") or result.get("validUntil")
        if tk:
            self.stdout.write(self.style.SUCCESS(f"  Student token minted! Valid: {ctx['m_student_valid']}"))

    def _step_46_verify_student(self, token: str, ctx: dict):
        """Verify student token."""
        tk = ctx.get("m_student_token")
        if not tk:
            self.stdout.write(self.style.WARNING("  Skipping - no student token"))
            return
        result = self._call("Account", "getMyAccountInfo", {}, tk)
        self.stdout.write(f"  Role: {result.get('role')}, Orgs: {result.get('organizations')}")

    def _step_47_idempotency(self, token: str, ctx: dict):
        """Re-create same teacher - should return same ID."""
        body = {
            "role": "TEACHER",
            "user_profile": {"first_name": "Test", "last_name": "PreplyTeacher"},
            "subject": "preply-test-teacher-001",
            "email": "test-teacher-001@preply-hackathon.example",
        }
        result = self._call("Account", "getOrCreateAccount", body, token)
        new_id = result.get("account_id") or result.get("accountId")
        original = ctx.get("m_teacher_id")
        if new_id == original:
            self.stdout.write(self.style.SUCCESS(f"  Idempotent! Same ID: {new_id}"))
        else:
            self.stdout.write(self.style.WARNING(f"  Different! Original: {original}, New: {new_id}"))

    def _step_48_existing_email(self, token: str, ctx: dict):
        """Try creating account with the admin's own email (existing user)."""
        body = {
            "role": "TEACHER",
            "user_profile": {"first_name": "Vasyl", "last_name": "Stanislavchuk"},
            "subject": "preply-admin-email-test",
            "email": "vasyl.stanislavchuk@gmail.com",
        }
        result = self._call("Account", "getOrCreateAccount", body, token)
        acct_id = result.get("account_id") or result.get("accountId")
        if acct_id:
            ctx["existing_email_id"] = acct_id
            self.stdout.write(self.style.SUCCESS(f"  Got account for existing email: {acct_id}"))
            # Is it the same as admin?
            admin_id = ctx.get("admin_classtime_id") or "v6b9rJEQL2IqrTXkJ_YyvQ"
            self.stdout.write(f"  Same as admin? {acct_id == admin_id}")

    def _step_24_update_org(self, token: str, ctx: dict):
        """Try updateOrganization to add members directly."""
        org_id = "b47a32f4-8656-4c8f-9c5c-92e8a69c1d37"
        admin_id = "v6b9rJEQL2IqrTXkJ_YyvQ"
        body = {
            "memberAccountIds": [admin_id],
            "organizationInfo": {
                "organizationId": org_id,
            },
        }
        result = self._call("Account", "updateOrganization", body, token)
        ctx["org_updated"] = "classtimeErrorCode" not in result
        if ctx["org_updated"]:
            self.stdout.write(self.style.SUCCESS("  Organization updated with members!"))
            # Verify
            result2 = self._call(
                "Account", "getOrganization", {"organizationId": org_id, "shouldIncludeAllMembers": True}, token
            )
            members = result2.get("organizationMembers", [])
            self.stdout.write(f"  Members after update: {len(members)}")
            for m in members:
                self.stdout.write(f"    - {m.get('accountRef', {}).get('id')}")

    def _step_25_final_mint(self, token: str, ctx: dict):
        """Final retry of createToken."""
        admin_id = "v6b9rJEQL2IqrTXkJ_YyvQ"
        # Check account info first
        result0 = self._call("Account", "getMyAccountInfo", {}, token)
        self.stdout.write(f"  Admin orgs now: {result0.get('organizations')}")
        # Try mint
        body = {"classtimeId": admin_id}
        result = self._call("Account", "createToken", body, token)
        if result.get("token"):
            ctx["final_token"] = result["token"]
            self.stdout.write(self.style.SUCCESS(f"  TOKEN MINTED! {result['token'][:80]}..."))
        else:
            self.stdout.write(self.style.ERROR("  Still can't mint. Need Classtime team to fix org setup."))

    def _step_18_explore_org(self, token: str, ctx: dict):
        """Explore the preply organization structure."""
        admin_id = ctx.get("admin_classtime_id") or "v6b9rJEQL2IqrTXkJ_YyvQ"

        # Get organizations for admin account
        self.stdout.write("  --- getOrganizations for admin ---")
        result = self._call("Account", "getOrganizations", {"accountId": admin_id}, token)
        orgs = result.get("organizations", [])
        for org in orgs:
            org_id = org.get("organizationId")
            ctx["org_id"] = org_id
            self.stdout.write(self.style.SUCCESS(f"  Org: {org_id}"))
            self.stdout.write(f"  Details: {_fmt(org)}")

        # Try getOrganization with org_id if we found one
        org_id = ctx.get("org_id")
        if org_id:
            self.stdout.write(f"  --- getOrganization {org_id} ---")
            result2 = self._call(
                "Account", "getOrganization", {"organizationId": org_id, "shouldIncludeAllMembers": True}, token
            )
            self.stdout.write(f"  Org details: {_fmt(result2)}")
            members = result2.get("organizationMembers", [])
            ctx["org_members"] = [m.get("accountRef", {}).get("id") for m in members]
            self.stdout.write(f"  Members count: {len(members)}")

        # Try findOrganizationsByTitle
        self.stdout.write("  --- findOrganizationsByTitle 'preply' ---")
        result3 = self._call("Account", "findOrganizationsByTitle", {"searchText": "preply"}, token)
        self.stdout.write(f"  Found: {_fmt(result3)}")

    def _step_19_associate_member(self, token: str, ctx: dict):
        """Try associating the admin account with the preply org."""
        org_id = ctx.get("org_id") or "b47a32f4-8656-4c8f-9c5c-92e8a69c1d37"
        admin_id = ctx.get("admin_classtime_id") or "v6b9rJEQL2IqrTXkJ_YyvQ"
        body = {"organizationId": org_id, "accountId": admin_id}
        result = self._call("Account", "associateMember", body, token)
        ctx["admin_associated_org"] = "classtimeErrorCode" not in result
        if ctx["admin_associated_org"]:
            self.stdout.write(self.style.SUCCESS("  Admin associated with org!"))

    def _step_20_retry_mint_after_org(self, token: str, ctx: dict):
        """Retry minting token after org association."""
        admin_id = ctx.get("admin_classtime_id") or "v6b9rJEQL2IqrTXkJ_YyvQ"
        body = {"classtimeId": admin_id}
        result = self._call("Account", "createToken", body, token)
        if result.get("token"):
            ctx["admin_minted_token"] = result["token"]
            self.stdout.write(
                self.style.SUCCESS(f"  Token minted after org association! Valid: {result.get('validUntil')}")
            )
        # Also try minting a TEACHER token specifically
        body2 = {"classtimeId": admin_id, "role": "TEACHER"}
        result2 = self._call("Account", "createToken", body2, token)
        if result2.get("token"):
            ctx["admin_teacher_token"] = result2["token"]
            self.stdout.write(self.style.SUCCESS("  Teacher-scoped token minted!"))
