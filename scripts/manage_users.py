#!/usr/bin/env python3
"""CLI utility to manage admin users and roles."""

import argparse
import sys
import uuid
from typing import Optional

# Ensure we can import from app
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.auth import hash_password
from app.db import admin_repo
from app.db.admin_repo import DatabaseUnavailable
from app.core.config import ROLE_SUPER_ADMIN, ROLE_PROJECT_ADMIN


from app.db.session import initialize_database, is_database_available


def create_user_cmd(args):
    if not is_database_available():
        if not initialize_database():
            print("Error: Could not initialize database.")
            return
    try:
        password_hash = hash_password(args.password)
        user = admin_repo.create_user(
            email=args.email,
            full_name=args.full_name,
            password_hash=password_hash
        )
        print(f"User created: {user['email']} (ID: {user['id']})")
        
        user_uuid = uuid.UUID(user['id'])
        
        if args.role:
            admin_repo.assign_global_role(user_uuid, args.role)
            print(f"Assigned global role: {args.role}")
            
        if args.project_id:
            for pid in args.project_id:
                admin_repo.add_project_membership(pid, user_uuid, ROLE_PROJECT_ADMIN)
                print(f"Assigned to project: {pid}")
                
    except ValueError as e:
        print(f"Error: {e}")
    except DatabaseUnavailable as e:
        print(f"Database Error: {e}")


def list_users_cmd(args):
    if not is_database_available():
        if not initialize_database():
            print("Error: Could not initialize database.")
            return
    try:
        users = admin_repo.list_users()
        print(f"{'Email':<30} | {'Roles':<20} | {'Active':<10} | {'Projects'}")
        print("-" * 80)
        for u in users:
            roles = ", ".join(u.get('roles', []))
            projects = ", ".join(u.get('project_ids', []))
            print(f"{u['email']:<30} | {roles:<20} | {str(u['is_active']):<10} | {projects}")
    except DatabaseUnavailable as e:
        print(f"Database Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Manage Admin Users")
    subparsers = parser.add_subparsers(dest="command")

    # Create user
    create_parser = subparsers.add_parser("create", help="Create a new user")
    create_parser.add_argument("--email", required=True, help="User email")
    create_parser.add_argument("--password", required=True, help="User password")
    create_parser.add_argument("--full-name", help="User full name")
    create_parser.add_argument("--role", choices=[ROLE_SUPER_ADMIN, ROLE_PROJECT_ADMIN], help="Global role")
    create_parser.add_argument("--project-id", nargs="+", help="Project IDs (for project_admin)")

    # List users
    subparsers.add_parser("list", help="List all users")

    args = parser.parse_args()

    if args.command == "create":
        create_user_cmd(args)
    elif args.command == "list":
        list_users_cmd(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
