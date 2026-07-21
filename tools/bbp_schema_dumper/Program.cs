// Dumper de schema de tipos do serializador binário de blueprints da Owlcat
// (Warhammer 40k Rogue Trader). Gera um JSON consumido por tools/bbp_parser.py.
//
// Baseado nas classes de schema do projeto MIT xADDBx/BpBinReader
// (reimplementação do ReflectionBasedSerializer do jogo via MetadataLoadContext).
//
// Uso: dotnet run -- <dir Managed do jogo> <saida.json>

using System.Reflection;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace BpBinReader;

public sealed class DumpingProvider : RogueTraderTypeSchemaProvider {
    private readonly Dictionary<Type, TypeSchema> m_ByType = new();
    private readonly HashSet<Type> m_InProgress = new();
    private readonly Type m_FlagsAttr;

    public DumpingProvider(IEnumerable<string> paths) : base(paths) {
        m_FlagsAttr = RequireType("System.FlagsAttribute");
    }

    // Quebra ciclos de tipos não-identificados: devolve um placeholder (campos
    // vazios) referenciado por FullName; a definição real entra no dicionário
    // quando o BuildSchema externo conclui.
    protected override TypeSchema BuildSchema(Type type, Guid typeId) {
        if (m_ByType.TryGetValue(type, out var cached)) {
            return cached;
        }
        if (!m_InProgress.Add(type)) {
            return new TypeSchema(type.Name, type.FullName ?? type.Name, [], type, typeId);
        }
        try {
            var s = base.BuildSchema(type, typeId);
            m_ByType[type] = s;
            return s;
        } finally {
            m_InProgress.Remove(type);
        }
    }

    public void DumpAll(string outPath) {
        var typeIds = new JsonObject();
        var types = new JsonObject();
        var enums = new JsonObject();
        var errors = new JsonObject();

        int ok = 0;
        foreach (var kv in TypeById) {
            TypeSchema s;
            try {
                s = Resolve(kv.Key);
            } catch (Exception e) {
                errors[kv.Key.ToString("N")] = e.Message;
                continue;
            }
            typeIds[kv.Key.ToString("N")] = s.FullName;
            AddType(s, types, enums);
            ok++;
        }
        Console.WriteLine($"Tipos com TypeId resolvidos: {ok}; falhas: {errors.Count}; tipos no schema: {types.Count}; enums: {enums.Count}");

        var root = new JsonObject {
            ["game"] = "RogueTrader",
            ["use_string_asset_id"] = UseStringAssetIdType,
            ["serialized_field_name"] = SerializedFieldName,
            ["type_ids"] = typeIds,
            ["types"] = types,
            ["enums"] = enums,
            ["errors"] = errors,
        };
        File.WriteAllText(outPath, root.ToJsonString(new JsonSerializerOptions { WriteIndented = false }));
        Console.WriteLine($"Escrito {outPath}");
    }

    private void AddType(TypeSchema s, JsonObject types, JsonObject enums) {
        if (types.TryGetPropertyValue(s.FullName, out var existing)) {
            var existingFields = (JsonArray)existing!["fields"]!;
            if (existingFields.Count > 0 || s.SerializedFields.Count == 0) {
                return; // definição real já registrada (ou placeholder redundante)
            }
        }
        var fields = new JsonArray();
        var obj = new JsonObject { ["name"] = s.Name, ["fields"] = fields };
        types[s.FullName] = obj; // registra antes de recursar (quebra ciclos)
        foreach (var f in s.SerializedFields) {
            fields.Add(new JsonObject {
                ["name"] = f.Name,
                ["value"] = SerializeValue(f.Value, types, enums),
            });
        }
    }

    private JsonObject SerializeValue(ValueSchema v, JsonObject types, JsonObject enums) {
        var o = new JsonObject { ["kind"] = v.Kind.ToString() };
        switch (v.Kind) {
            case ValueKind.Array:
            case ValueKind.List:
                o["element"] = SerializeValue(v.Element!, types, enums);
                break;
            case ValueKind.EnumInt32: {
                    var et = v.ObjectType!;
                    o["enum"] = et.FullName;
                    if (!enums.ContainsKey(et.FullName)) {
                        var values = new JsonObject();
                        foreach (var f in et.Type.GetFields(BindingFlags.Public | BindingFlags.Static)) {
                            try {
                                values[f.Name] = Convert.ToInt64(f.GetRawConstantValue());
                            } catch { }
                        }
                        enums[et.FullName] = new JsonObject {
                            ["is_flags"] = HasAttribute(et.Type, m_FlagsAttr),
                            ["values"] = values,
                        };
                    }
                    break;
                }
            case ValueKind.Object:
                o["identified"] = v.IsIdentifiedType;
                if (v.ForceNeedsType) {
                    o["force_needs_type"] = true;
                }
                if (!v.IsIdentifiedType) {
                    o["type"] = v.ObjectType!.FullName;
                    AddType(v.ObjectType!, types, enums);
                }
                break;
        }
        return o;
    }
}

public static class DumperEntry {
    public static void Main(string[] args) {
        if (args.Length != 2) {
            Console.WriteLine("Uso: BbpSchemaDumper <dir Managed> <saida.json>");
            Environment.Exit(1);
        }
        using var provider = new DumpingProvider([args[0]]);
        provider.DumpAll(args[1]);
    }
}
