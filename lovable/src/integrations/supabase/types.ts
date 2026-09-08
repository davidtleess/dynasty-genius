export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5";
  };
  public: {
    Tables: {
      draft_picks: {
        Row: {
          id: number;
          original_roster_id: number;
          owner_roster_id: number;
          round: number;
          season: string;
          updated_at: string;
        };
        Insert: {
          id?: number;
          original_roster_id: number;
          owner_roster_id: number;
          round: number;
          season: string;
          updated_at?: string;
        };
        Update: {
          id?: number;
          original_roster_id?: number;
          owner_roster_id?: number;
          round?: number;
          season?: string;
          updated_at?: string;
        };
        Relationships: [];
      };
      league_teams: {
        Row: {
          avatar: string | null;
          display_name: string | null;
          is_mine: boolean;
          losses: number | null;
          owner_id: string | null;
          points_for: number | null;
          roster_id: number;
          team_name: string | null;
          ties: number | null;
          updated_at: string;
          wins: number | null;
        };
        Insert: {
          avatar?: string | null;
          display_name?: string | null;
          is_mine?: boolean;
          losses?: number | null;
          owner_id?: string | null;
          points_for?: number | null;
          roster_id: number;
          team_name?: string | null;
          ties?: number | null;
          updated_at?: string;
          wins?: number | null;
        };
        Update: {
          avatar?: string | null;
          display_name?: string | null;
          is_mine?: boolean;
          losses?: number | null;
          owner_id?: string | null;
          points_for?: number | null;
          roster_id?: number;
          team_name?: string | null;
          ties?: number | null;
          updated_at?: string;
          wins?: number | null;
        };
        Relationships: [];
      };
      league_transactions: {
        Row: {
          adds: Json | null;
          created_at: string;
          created_ms: number | null;
          draft_picks: Json | null;
          drops: Json | null;
          raw: Json | null;
          roster_ids: number[] | null;
          status: string | null;
          transaction_id: string;
          type: string | null;
          week: number | null;
        };
        Insert: {
          adds?: Json | null;
          created_at?: string;
          created_ms?: number | null;
          draft_picks?: Json | null;
          drops?: Json | null;
          raw?: Json | null;
          roster_ids?: number[] | null;
          status?: string | null;
          transaction_id: string;
          type?: string | null;
          week?: number | null;
        };
        Update: {
          adds?: Json | null;
          created_at?: string;
          created_ms?: number | null;
          draft_picks?: Json | null;
          drops?: Json | null;
          raw?: Json | null;
          roster_ids?: number[] | null;
          status?: string | null;
          transaction_id?: string;
          type?: string | null;
          week?: number | null;
        };
        Relationships: [];
      };
      player_days: {
        Row: {
          created_at: string;
          id: number;
          margin: number | null;
          margin_pct: number | null;
          market_pos_rank: number | null;
          market_rank: number | null;
          market_value: number | null;
          model_version: string | null;
          our_pos_rank: number | null;
          our_rank: number | null;
          our_value: number | null;
          player_id: string;
          rank_margin: number | null;
          receipts: Json | null;
          snapshot_date: string;
          tier: string | null;
          tier_basis: Json | null;
        };
        Insert: {
          created_at?: string;
          id?: number;
          margin?: number | null;
          margin_pct?: number | null;
          market_pos_rank?: number | null;
          market_rank?: number | null;
          market_value?: number | null;
          model_version?: string | null;
          our_pos_rank?: number | null;
          our_rank?: number | null;
          our_value?: number | null;
          player_id: string;
          rank_margin?: number | null;
          receipts?: Json | null;
          snapshot_date: string;
          tier?: string | null;
          tier_basis?: Json | null;
        };
        Update: {
          created_at?: string;
          id?: number;
          margin?: number | null;
          margin_pct?: number | null;
          market_pos_rank?: number | null;
          market_rank?: number | null;
          market_value?: number | null;
          model_version?: string | null;
          our_pos_rank?: number | null;
          our_rank?: number | null;
          our_value?: number | null;
          player_id?: string;
          rank_margin?: number | null;
          receipts?: Json | null;
          snapshot_date?: string;
          tier?: string | null;
          tier_basis?: Json | null;
        };
        Relationships: [
          {
            foreignKeyName: "player_days_player_id_fkey";
            columns: ["player_id"];
            isOneToOne: false;
            referencedRelation: "players";
            referencedColumns: ["player_id"];
          },
        ];
      };
      players: {
        Row: {
          active: boolean;
          age: number | null;
          birth_date: string | null;
          college: string | null;
          draft_pick: number | null;
          draft_round: number | null;
          draft_year: number | null;
          fantasycalc_id: string | null;
          first_name: string | null;
          full_name: string;
          headshot_url: string | null;
          injury_status: string | null;
          last_name: string | null;
          player_id: string;
          position: string | null;
          status: string | null;
          team: string | null;
          updated_at: string;
          years_exp: number | null;
        };
        Insert: {
          active?: boolean;
          age?: number | null;
          birth_date?: string | null;
          college?: string | null;
          draft_pick?: number | null;
          draft_round?: number | null;
          draft_year?: number | null;
          fantasycalc_id?: string | null;
          first_name?: string | null;
          full_name: string;
          headshot_url?: string | null;
          injury_status?: string | null;
          last_name?: string | null;
          player_id: string;
          position?: string | null;
          status?: string | null;
          team?: string | null;
          updated_at?: string;
          years_exp?: number | null;
        };
        Update: {
          active?: boolean;
          age?: number | null;
          birth_date?: string | null;
          college?: string | null;
          draft_pick?: number | null;
          draft_round?: number | null;
          draft_year?: number | null;
          fantasycalc_id?: string | null;
          first_name?: string | null;
          full_name?: string;
          headshot_url?: string | null;
          injury_status?: string | null;
          last_name?: string | null;
          player_id?: string;
          position?: string | null;
          status?: string | null;
          team?: string | null;
          updated_at?: string;
          years_exp?: number | null;
        };
        Relationships: [];
      };
      roster_players: {
        Row: {
          id: number;
          player_id: string;
          roster_id: number;
          slot: string;
          updated_at: string;
        };
        Insert: {
          id?: number;
          player_id: string;
          roster_id: number;
          slot?: string;
          updated_at?: string;
        };
        Update: {
          id?: number;
          player_id?: string;
          roster_id?: number;
          slot?: string;
          updated_at?: string;
        };
        Relationships: [
          {
            foreignKeyName: "roster_players_roster_id_fkey";
            columns: ["roster_id"];
            isOneToOne: false;
            referencedRelation: "league_teams";
            referencedColumns: ["roster_id"];
          },
        ];
      };
      sync_runs: {
        Row: {
          detail: Json | null;
          finished_at: string | null;
          id: number;
          rows_written: number | null;
          source: string;
          started_at: string;
          status: string;
        };
        Insert: {
          detail?: Json | null;
          finished_at?: string | null;
          id?: number;
          rows_written?: number | null;
          source: string;
          started_at?: string;
          status: string;
        };
        Update: {
          detail?: Json | null;
          finished_at?: string | null;
          id?: number;
          rows_written?: number | null;
          source?: string;
          started_at?: string;
          status?: string;
        };
        Relationships: [];
      };
      watchlist: {
        Row: {
          created_at: string;
          id: number;
          note: string | null;
          player_id: string;
          user_id: string;
        };
        Insert: {
          created_at?: string;
          id?: number;
          note?: string | null;
          player_id: string;
          user_id: string;
        };
        Update: {
          created_at?: string;
          id?: number;
          note?: string | null;
          player_id?: string;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "watchlist_player_id_fkey";
            columns: ["player_id"];
            isOneToOne: false;
            referencedRelation: "players";
            referencedColumns: ["player_id"];
          },
        ];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      [_ in never]: never;
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
};

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">;

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">];

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R;
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] & DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R;
      }
      ? R
      : never
    : never;

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    keyof DefaultSchema["Tables"] | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I;
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I;
      }
      ? I
      : never
    : never;

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    keyof DefaultSchema["Tables"] | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U;
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U;
      }
      ? U
      : never
    : never;

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    keyof DefaultSchema["Enums"] | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never;

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    keyof DefaultSchema["CompositeTypes"] | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never;

export const Constants = {
  public: {
    Enums: {},
  },
} as const;
