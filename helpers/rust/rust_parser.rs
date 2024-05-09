use syn::{parse_file, ImplItem, Item, Type};
use syn::__private::ToTokens;
use syn::spanned::Spanned;
use proc_macro2::Span;
use std::env;
use std::fs;
use std::fmt;
use std::path::Path;
use serde::Serialize;
use serde_json;

#[derive(Serialize)]
struct ModuleObject {
    name: String,
    #[serde(rename = "type")]
    kind: String,
    source: String,
    receiver: Option<String>,
}

#[derive(Serialize)]
struct ImplDetails {
    impl_for: String,
    methods: Vec<ModuleObject>,
}

fn extract_source_code(span: Span, file_content: &str) -> String {
    let start = span.start().line - 1; // Line numbers in Span are 1-indexed
    let end = span.end().line;

    file_content.lines()
        .skip(start)
        .take(end - start)
        .collect::<Vec<&str>>()
        .join("\n")
}

fn type_to_string(ty: &Box<Type>) -> String {
    ty.to_token_stream().to_string()
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("Usage: rust_parser <file_path>");
        std::process::exit(1);
    }

    let file_path = Path::new(&args[1]);
    if !file_path.exists() {
        eprintln!("File does not exist: {}", file_path.display());
        std::process::exit(1);
    }

    let content = fs::read_to_string(file_path).expect("Error reading file");
    let syntax_tree = parse_file(&content).expect("Error parsing file");

    let mut module_objects = Vec::new();

    for item in syntax_tree.items {
        let (name, kind, source) = match item {
            Item::Use(item_use) => {
                let source_code = extract_source_code(item_use.span(), &content);
                (item_use.tree.into_token_stream().to_string(), "use".to_string(), source_code)
            },
            Item::Struct(item_struct) => {
                let source_code = extract_source_code(item_struct.span(), &content);
                (item_struct.ident.to_string(), "struct".to_string(), source_code)
            },
            Item::Fn(item_fn) => {
                let source_code = extract_source_code(item_fn.span(), &content);
                (item_fn.sig.ident.to_string(), "function".to_string(), source_code)
            },
            Item::Mod(item_mod) => {
                let source_code = extract_source_code(item_mod.span(), &content);
                (item_mod.ident.to_string(), "module".to_string(), source_code)
            },
            Item::Const(item_const) => {
                let source_code = extract_source_code(item_const.span(), &content);
                (item_const.ident.to_string(), "const".to_string(), source_code)
            },
            Item::Trait(item_trait) => {
                let source_code = extract_source_code(item_trait.span(), &content);
                (item_trait.ident.to_string(), "trait".to_string(), source_code)
            },
            Item::Enum(item_enum) => {
                let source_code = extract_source_code(item_enum.span(), &content);
                (item_enum.ident.to_string(), "enum".to_string(), source_code)
            },
            Item::Macro(item_macro) => {
                let source_code = extract_source_code(item_macro.span(), &content);
                match item_macro.ident {
                    Some(ident) => (ident.to_string(), "macro".to_string(), source_code),
                    None => ("unknown macro".to_string(), "macro".to_string(), source_code)
                }
            },
            Item::Static(item_static) => {
                let source_code = extract_source_code(item_static.span(), &content);
                (item_static.ident.to_string(), "static".to_string(), source_code)
            },
            Item::Union(item_union) => {
                let source_code = extract_source_code(item_union.span(), &content);
                (item_union.ident.to_string(), "union".to_string(), source_code)
            },
            Item::Type(item_type) => {
                let source_code = extract_source_code(item_type.span(), &content);
                (item_type.ident.to_string(), "type".to_string(), source_code)
            },
            Item::Impl(item_impl) => {
                let impl_name = type_to_string(&item_impl.self_ty);
                let source_code = extract_source_code(item_impl.span(), &content);

                //let mut methods = Vec::new();

                for impl_item in item_impl.items {
                    if let ImplItem::Method(method) = impl_item {
                        let method_name = method.sig.ident.to_string();
                        let source_code = extract_source_code(method.span(), &content);
                        module_objects.push(ModuleObject {
                            name: method_name,
                            kind: "method".to_string(),
                            source: source_code,
                            receiver: Some(impl_name.clone()),
                        });
                    }
                }

                (impl_name, "impl".to_string(), source_code)
            },
            _ => {
                let source_code = extract_source_code(item.span(), &content);
                let name = fmt::format(format_args!("{:?}", item));
                (name.to_string(), "item".to_string(), source_code)
            }
        };

        module_objects.push(ModuleObject { name, kind, source, receiver: None });
    }

    println!("{}", serde_json::to_string(&module_objects).unwrap());
}