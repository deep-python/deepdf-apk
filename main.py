import os
import flet as ft
from pypdf import PdfReader, PdfWriter
from PIL import Image, ImageOps


def parse_page_ranges(range_str, max_pages):
    """1-based page range string ('3, 1, 2, 5-7') ko 0-based indices list mein badalta hai."""
    indices = []
    if not range_str or not range_str.strip():
        return indices
    parts = [p.strip() for p in range_str.split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s.strip()), int(end_s.strip())
            if start < 1 or end < 1 or start > max_pages or end > max_pages:
                raise ValueError(f"Page range '{part}' (1-{max_pages}) ke bahar hai.")
            step = 1 if start <= end else -1
            for p in range(start, end + step, step):
                indices.append(p - 1)
        else:
            p = int(part)
            if p < 1 or p > max_pages:
                raise ValueError(f"Page number '{p}' (1-{max_pages}) ke bahar hai.")
            indices.append(p - 1)
    return indices


def get_output_dir(sample_path=None):
    """Android Download folder ya input file ke folder mein save path banata hai."""
    android_dl = "/storage/emulated/0/Download"
    if os.path.isdir(android_dl) and os.access(android_dl, os.W_OK):
        return android_dl
    if sample_path and os.path.dirname(sample_path):
        parent = os.path.dirname(sample_path)
        if os.access(parent, os.W_OK):
            return parent
    return os.path.expanduser("~")


def main(page: ft.Page):
    page.title = "DeePDF Studio"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0f172a"
    page.padding = 0

    status_text = ft.Text("Ready", size=12, color="#94a3b8")

    def notify(msg, is_error=False):
        status_text.value = msg
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color="#ffffff"),
            bgcolor="#ef4444" if is_error else "#10b981",
        )
        page.snack_bar.open = True
        page.update()

    # File Pickers
    fp_single = ft.FilePicker()
    fp_second = ft.FilePicker()
    fp_multi_pdf = ft.FilePicker()
    fp_images = ft.FilePicker()
    page.overlay.extend([fp_single, fp_second, fp_multi_pdf, fp_images])

    # =========================================================================
    # 1. ADD PAGES
    # =========================================================================
    add_base_path = ft.Text("No Base PDF selected", size=12, color="#94a3b8")
    add_src_path = ft.Text("No Source PDF selected", size=12, color="#94a3b8")
    add_mode = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="pdf", label="From Another PDF"),
            ft.Radio(value="blank", label="Blank Page(s)"),
        ]),
        value="pdf",
    )
    add_pos = ft.TextField(label="Insert at Position (1=Start, 0=End)", value="1", bgcolor="#1e293b")
    add_range = ft.TextField(label="Pages ('all' or '1, 3-5') / Blank Count", value="all", bgcolor="#1e293b")
    add_out_name = ft.TextField(label="Output File Name", value="deepdf_added.pdf", bgcolor="#1e293b")

    def pick_add_base(_):
        def on_res(e: ft.FilePickerResultEvent):
            if e.files:
                add_base_path.value = e.files[0].path
                page.update()
        fp_single.on_result = on_res
        fp_single.pick_files(allowed_extensions=["pdf"])

    def pick_add_src(_):
        def on_res(e: ft.FilePickerResultEvent):
            if e.files:
                add_src_path.value = e.files[0].path
                page.update()
        fp_second.on_result = on_res
        fp_second.pick_files(allowed_extensions=["pdf"])

    def run_add_pages(_):
        b_path = add_base_path.value
        if not b_path or not os.path.isfile(b_path):
            return notify("Please select a valid Base PDF file.", True)
        try:
            base_reader = PdfReader(b_path)
            total_base = len(base_reader.pages)
            pos = int(add_pos.value.strip() or "1")
            insert_idx = total_base if pos <= 0 or pos > total_base else pos - 1

            writer = PdfWriter()
            for i in range(insert_idx):
                writer.add_page(base_reader.pages[i])

            if add_mode.value == "pdf":
                s_path = add_src_path.value
                if not s_path or not os.path.isfile(s_path):
                    return notify("Please select a valid Source PDF file.", True)
                src_reader = PdfReader(s_path)
                r_txt = add_range.value.strip().lower()
                src_indices = list(range(len(src_reader.pages))) if r_txt in ("all", "") else parse_page_ranges(r_txt, len(src_reader.pages))
                for idx in src_indices:
                    writer.add_page(src_reader.pages[idx])
            else:
                r_txt = add_range.value.strip().lower()
                count = 1 if r_txt == "all" else max(1, int(r_txt))
                w = float(base_reader.pages[0].mediabox.width) if total_base > 0 else 595.0
                h = float(base_reader.pages[0].mediabox.height) if total_base > 0 else 842.0
                for _ in range(count):
                    writer.add_blank_page(width=w, height=h)

            for i in range(insert_idx, total_base):
                writer.add_page(base_reader.pages[i])

            out_file = os.path.join(get_output_dir(b_path), add_out_name.value.strip() or "deepdf_added.pdf")
            with open(out_file, "wb") as f:
                writer.write(f)
            notify(f"Saved: {out_file}")
        except Exception as ex:
            notify(str(ex), True)

    tab_add = ft.Container(
        padding=16,
        content=ft.Column([
            ft.Text("1. Add Page(s) at Specific Location", size=18, weight=ft.FontWeight.BOLD, color="#38bdf8"),
            ft.ElevatedButton("Select Base PDF", on_click=pick_add_base, bgcolor="#2563eb", color="#ffffff"),
            add_base_path,
            add_mode,
            ft.ElevatedButton("Select Source PDF", on_click=pick_add_src, bgcolor="#2563eb", color="#ffffff"),
            add_src_path,
            add_pos,
            add_range,
            add_out_name,
            ft.ElevatedButton("Insert Pages & Save PDF", on_click=run_add_pages, bgcolor="#10b981", color="#ffffff"),
        ], scroll=ft.ScrollMode.AUTO),
    )

    # =========================================================================
    # 2. DELETE PAGES
    # =========================================================================
    del_pdf_path = ft.Text("No PDF selected", size=12, color="#94a3b8")
    del_range = ft.TextField(label="Pages to Delete (e.g., 1, 3, 5-8)", bgcolor="#1e293b")
    del_out_name = ft.TextField(label="Output File Name", value="deepdf_deleted.pdf", bgcolor="#1e293b")

    def pick_del_pdf(_):
        def on_res(e: ft.FilePickerResultEvent):
            if e.files:
                p = e.files[0].path
                try:
                    cnt = len(PdfReader(p).pages)
                    del_pdf_path.value = f"{p} ({cnt} pages)"
                    del_pdf_path.data = p
                except Exception:
                    del_pdf_path.value = p
                    del_pdf_path.data = p
                page.update()
        fp_single.on_result = on_res
        fp_single.pick_files(allowed_extensions=["pdf"])

    def run_delete_pages(_):
        p = getattr(del_pdf_path, "data", None)
        if not p or not os.path.isfile(p):
            return notify("Please select a valid PDF file.", True)
        try:
            reader = PdfReader(p)
            total = len(reader.pages)
            to_del = set(parse_page_ranges(del_range.value, total))
            if not to_del:
                return notify("Specify at least one page to delete.", True)
            if len(to_del) >= total:
                return notify("Cannot delete all pages from a PDF.", True)

            writer = PdfWriter()
            for i in range(total):
                if i not in to_del:
                    writer.add_page(reader.pages[i])

            out_file = os.path.join(get_output_dir(p), del_out_name.value.strip() or "deepdf_deleted.pdf")
            with open(out_file, "wb") as f:
                writer.write(f)
            notify(f"Deleted {len(to_del)} page(s)! Saved: {out_file}")
        except Exception as ex:
            notify(str(ex), True)

    tab_del = ft.Container(
        padding=16,
        content=ft.Column([
            ft.Text("2. Delete Page(s) from PDF", size=18, weight=ft.FontWeight.BOLD, color="#38bdf8"),
            ft.ElevatedButton("Select PDF File", on_click=pick_del_pdf, bgcolor="#2563eb", color="#ffffff"),
            del_pdf_path,
            del_range,
            del_out_name,
            ft.ElevatedButton("Delete Pages & Save PDF", on_click=run_delete_pages, bgcolor="#10b981", color="#ffffff"),
        ], scroll=ft.ScrollMode.AUTO),
    )

    # =========================================================================
    # 3. ORGANIZE / REORDER PAGES (WITH CUSTOM PAGE ORDER INPUT FIELD)
    # =========================================================================
    org_pdf_path = ft.Text("No PDF selected", size=12, color="#94a3b8")
    org_custom_order = ft.TextField(
        label="Custom Page Order (e.g., 3, 1, 2, 4-6)",
        bgcolor="#1e293b",
    )
    org_out_name = ft.TextField(label="Output File Name", value="deepdf_organized.pdf", bgcolor="#1e293b")
    org_list_view = ft.Column(spacing=4)
    org_state = {"path": None, "total": 0, "indices": []}

    def sync_org_ui():
        org_custom_order.value = ", ".join(str(i + 1) for i in org_state["indices"])
        org_list_view.controls.clear()
        for pos, orig_idx in enumerate(org_state["indices"], start=1):
            org_list_view.controls.append(
                ft.Text(f"Position {pos}  ➔  Original Page #{orig_idx + 1}", size=13, color="#e2e8f0")
            )
        page.update()

    def pick_org_pdf(_):
        def on_res(e: ft.FilePickerResultEvent):
            if e.files:
                p = e.files[0].path
                try:
                    reader = PdfReader(p)
                    org_state["path"] = p
                    org_state["total"] = len(reader.pages)
                    org_state["indices"] = list(range(org_state["total"]))
                    org_pdf_path.value = f"{p} ({org_state['total']} pages)"
                    sync_org_ui()
                except Exception as ex:
                    notify(str(ex), True)
        fp_single.on_result = on_res
        fp_single.pick_files(allowed_extensions=["pdf"])

    def apply_custom_org(_):
        if not org_state["total"]:
            return notify("Select a PDF file first.", True)
        try:
            org_state["indices"] = parse_page_ranges(org_custom_order.value, org_state["total"])
            sync_org_ui()
            notify("Custom page order applied!")
        except Exception as ex:
            notify(str(ex), True)

    def reverse_org(_):
        org_state["indices"].reverse()
        sync_org_ui()

    def run_org_save(_):
        p = org_state["path"]
        if not p or not os.path.isfile(p):
            return notify("Please select a PDF file first.", True)
        try:
            reader = PdfReader(p)
            if org_custom_order.value.strip():
                org_state["indices"] = parse_page_ranges(org_custom_order.value, len(reader.pages))
                sync_org_ui()
            writer = PdfWriter()
            for idx in org_state["indices"]:
                writer.add_page(reader.pages[idx])
            out_file = os.path.join(get_output_dir(p), org_out_name.value.strip() or "deepdf_organized.pdf")
            with open(out_file, "wb") as f:
                writer.write(f)
            notify(f"Reordered PDF saved: {out_file}")
        except Exception as ex:
            notify(str(ex), True)

    tab_org = ft.Container(
        padding=16,
        content=ft.Column([
            ft.Text("3. Organize & Reorder Pages", size=18, weight=ft.FontWeight.BOLD, color="#38bdf8"),
            ft.ElevatedButton("Select PDF File", on_click=pick_org_pdf, bgcolor="#2563eb", color="#ffffff"),
            org_pdf_path,
            org_custom_order,
            ft.Row([
                ft.ElevatedButton("Apply Custom Order", on_click=apply_custom_org, bgcolor="#2563eb", color="#ffffff"),
                ft.ElevatedButton("Reverse All", on_click=reverse_org, bgcolor="#334155", color="#ffffff"),
            ]),
            ft.Container(content=org_list_view, bgcolor="#1e293b", padding=10, border_radius=8),
            org_out_name,
            ft.ElevatedButton("Save Reordered PDF", on_click=run_org_save, bgcolor="#10b981", color="#ffffff"),
        ], scroll=ft.ScrollMode.AUTO),
    )

    # =========================================================================
    # 4. COMPRESS PDF
    # =========================================================================
    comp_pdf_path = ft.Text("No PDF selected", size=12, color="#94a3b8")
    comp_level = ft.RadioGroup(
        content=ft.Column([
            ft.Radio(value="extreme", label="Extreme Compression (Smallest Size - 45% Image Quality)"),
            ft.Radio(value="medium", label="Recommended Compression (70% Image Quality)"),
            ft.Radio(value="lossless", label="Lossless Content Deflate Only"),
        ]),
        value="extreme",
    )
    comp_out_name = ft.TextField(label="Output File Name", value="deepdf_compressed.pdf", bgcolor="#1e293b")

    def pick_comp_pdf(_):
        def on_res(e: ft.FilePickerResultEvent):
            if e.files:
                comp_pdf_path.value = e.files[0].path
                page.update()
        fp_single.on_result = on_res
        fp_single.pick_files(allowed_extensions=["pdf"])

    def run_compress(_):
        p = comp_pdf_path.value
        if not p or not os.path.isfile(p):
            return notify("Please select a valid PDF file.", True)
        try:
            orig_size = os.path.getsize(p)
            reader = PdfReader(p)
            writer = PdfWriter()
            for pg in reader.pages:
                writer.add_page(pg)

            lvl = comp_level.value
            qual = 45 if lvl == "extreme" else 70
            for pg in writer.pages:
                if lvl in ("extreme", "medium"):
                    for img in pg.images:
                        try:
                            pil_img = img.image
                            if pil_img.mode in ("RGBA", "P"):
                                pil_img = pil_img.convert("RGB")
                            if lvl == "extreme" and (pil_img.width > 1200 or pil_img.height > 1200):
                                pil_img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                            img.replace(pil_img, quality=qual)
                        except Exception:
                            pass
                pg.compress_content_streams()

            writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
            out_file = os.path.join(get_output_dir(p), comp_out_name.value.strip() or "deepdf_compressed.pdf")
            with open(out_file, "wb") as f:
                writer.write(f)
            new_size = os.path.getsize(out_file)
            saved = max(0.0, (1 - (new_size / orig_size)) * 100) if orig_size > 0 else 0
            notify(f"Saved {saved:.1f}%! ({orig_size/1024:.1f}KB -> {new_size/1024:.1f}KB) File: {out_file}")
        except Exception as ex:
            notify(str(ex), True)

    tab_comp = ft.Container(
        padding=16,
        content=ft.Column([
            ft.Text("4. Compress PDF to Low Size", size=18, weight=ft.FontWeight.BOLD, color="#38bdf8"),
            ft.ElevatedButton("Select PDF to Compress", on_click=pick_comp_pdf, bgcolor="#2563eb", color="#ffffff"),
            comp_pdf_path,
            comp_level,
            comp_out_name,
            ft.ElevatedButton("Compress & Save PDF", on_click=run_compress, bgcolor="#10b981", color="#ffffff"),
        ], scroll=ft.ScrollMode.AUTO),
    )

    # =========================================================================
    # 5. MERGE PDFS
    # =========================================================================
    merge_files = []
    merge_list_ui = ft.Column(spacing=4)
    merge_out_name = ft.TextField(label="Output File Name", value="deepdf_merged.pdf", bgcolor="#1e293b")

    def refresh_merge_ui():
        merge_list_ui.controls.clear()
        for i, fp in enumerate(merge_files, start=1):
            merge_list_ui.controls.append(ft.Text(f"{i}. {os.path.basename(fp)}", size=13, color="#e2e8f0"))
        page.update()

    def add_merge_pdfs(_):
        def on_res(e: ft.FilePickerResultEvent):
            if e.files:
                for f in e.files:
                    merge_files.append(f.path)
                refresh_merge_ui()
        fp_multi_pdf.on_result = on_res
        fp_multi_pdf.pick_files(allow_multiple=True, allowed_extensions=["pdf"])

    def clear_merge_pdfs(_):
        merge_files.clear()
        refresh_merge_ui()

    def run_merge(_):
        if len(merge_files) < 2:
            return notify("Add at least 2 PDF files to merge.", True)
        try:
            writer = PdfWriter()
            for fp in merge_files:
                writer.append(fp)
            out_file = os.path.join(get_output_dir(merge_files[0]), merge_out_name.value.strip() or "deepdf_merged.pdf")
            with open(out_file, "wb") as f:
                writer.write(f)
            notify(f"Merged {len(merge_files)} PDFs! Saved: {out_file}")
        except Exception as ex:
            notify(str(ex), True)

    tab_merge = ft.Container(
        padding=16,
        content=ft.Column([
            ft.Text("5. Merge Two or More PDFs", size=18, weight=ft.FontWeight.BOLD, color="#38bdf8"),
            ft.Row([
                ft.ElevatedButton("+ Add PDF Files", on_click=add_merge_pdfs, bgcolor="#2563eb", color="#ffffff"),
                ft.ElevatedButton("Clear List", on_click=clear_merge_pdfs, bgcolor="#334155", color="#ffffff"),
            ]),
            ft.Container(content=merge_list_ui, bgcolor="#1e293b", padding=10, border_radius=8),
            merge_out_name,
            ft.ElevatedButton("Merge PDFs & Save", on_click=run_merge, bgcolor="#10b981", color="#ffffff"),
        ], scroll=ft.ScrollMode.AUTO),
    )

    # =========================================================================
    # 6. UNLOCK PDF
    # =========================================================================
    unlock_pdf_path = ft.Text("No PDF selected", size=12, color="#94a3b8")
    unlock_pwd = ft.TextField(label="Enter PDF Password", password=True, can_reveal_password=True, bgcolor="#1e293b")
    unlock_out_name = ft.TextField(label="Output File Name", value="deepdf_unlocked.pdf", bgcolor="#1e293b")

    def pick_unlock_pdf(_):
        def on_res(e: ft.FilePickerResultEvent):
            if e.files:
                unlock_pdf_path.value = e.files[0].path
                page.update()
        fp_single.on_result = on_res
        fp_single.pick_files(allowed_extensions=["pdf"])

    def run_unlock(_):
        p = unlock_pdf_path.value
        if not p or not os.path.isfile(p):
            return notify("Please select a valid PDF file.", True)
        try:
            reader = PdfReader(p)
            if reader.is_encrypted:
                if reader.decrypt(unlock_pwd.value) == 0:
                    return notify("Incorrect password! Could not unlock PDF.", True)
            writer = PdfWriter()
            for pg in reader.pages:
                writer.add_page(pg)
            out_file = os.path.join(get_output_dir(p), unlock_out_name.value.strip() or "deepdf_unlocked.pdf")
            with open(out_file, "wb") as f:
                writer.write(f)
            notify(f"Unlocked PDF saved: {out_file}")
        except Exception as ex:
            notify(str(ex), True)

    tab_unlock = ft.Container(
        padding=16,
        content=ft.Column([
            ft.Text("6. Unlock Password-Protected PDF", size=18, weight=ft.FontWeight.BOLD, color="#38bdf8"),
            ft.ElevatedButton("Select Locked PDF", on_click=pick_unlock_pdf, bgcolor="#2563eb", color="#ffffff"),
            unlock_pdf_path,
            unlock_pwd,
            unlock_out_name,
            ft.ElevatedButton("Unlock & Save PDF", on_click=run_unlock, bgcolor="#10b981", color="#ffffff"),
        ], scroll=ft.ScrollMode.AUTO),
    )

    # =========================================================================
    # 7. PROTECT PDF
    # =========================================================================
    prot_pdf_path = ft.Text("No PDF selected", size=12, color="#94a3b8")
    prot_user_pwd = ft.TextField(label="User Password (Required to Open)", password=True, can_reveal_password=True, bgcolor="#1e293b")
    prot_owner_pwd = ft.TextField(label="Owner Password (Optional)", password=True, can_reveal_password=True, bgcolor="#1e293b")
    prot_out_name = ft.TextField(label="Output File Name", value="deepdf_protected.pdf", bgcolor="#1e293b")

    def pick_prot_pdf(_):
        def on_res(e: ft.FilePickerResultEvent):
            if e.files:
                prot_pdf_path.value = e.files[0].path
                page.update()
        fp_single.on_result = on_res
        fp_single.pick_files(allowed_extensions=["pdf"])

    def run_protect(_):
        p = prot_pdf_path.value
        u_pwd = prot_user_pwd.value
        o_pwd = prot_owner_pwd.value or u_pwd
        if not p or not os.path.isfile(p):
            return notify("Please select a valid PDF file.", True)
        if not u_pwd:
            return notify("Please enter a password.", True)
        try:
            reader = PdfReader(p)
            writer = PdfWriter()
            for pg in reader.pages:
                writer.add_page(pg)
            try:
                writer.encrypt(user_password=u_pwd, owner_password=o_pwd, algorithm="AES-256")
            except Exception:
                writer.encrypt(user_password=u_pwd, owner_password=o_pwd, algorithm="RC4-128")
            out_file = os.path.join(get_output_dir(p), prot_out_name.value.strip() or "deepdf_protected.pdf")
            with open(out_file, "wb") as f:
                writer.write(f)
            notify(f"Protected PDF saved: {out_file}")
        except Exception as ex:
            notify(str(ex), True)

    tab_protect = ft.Container(
        padding=16,
        content=ft.Column([
            ft.Text("7. Protect PDF with Password", size=18, weight=ft.FontWeight.BOLD, color="#38bdf8"),
            ft.ElevatedButton("Select PDF to Protect", on_click=pick_prot_pdf, bgcolor="#2563eb", color="#ffffff"),
            prot_pdf_path,
            prot_user_pwd,
            prot_owner_pwd,
            prot_out_name,
            ft.ElevatedButton("Encrypt & Save Protected PDF", on_click=run_protect, bgcolor="#10b981", color="#ffffff"),
        ], scroll=ft.ScrollMode.AUTO),
    )

    # =========================================================================
    # 8. SCAN TO PDF
    # =========================================================================
    scan_files = []
    scan_list_ui = ft.Column(spacing=4)
    scan_filter = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="enhance", label="Auto-Enhance"),
            ft.Radio(value="bw", label="B&W Clean Scan"),
            ft.Radio(value="color", label="Original Color"),
        ]),
        value="enhance",
    )
    scan_out_name = ft.TextField(label="Output File Name", value="deepdf_scanned.pdf", bgcolor="#1e293b")

    def refresh_scan_ui():
        scan_list_ui.controls.clear()
        for i, fp in enumerate(scan_files, start=1):
            scan_list_ui.controls.append(ft.Text(f"{i}. {os.path.basename(fp)}", size=13, color="#e2e8f0"))
        page.update()

    def add_scan_imgs(_):
        def on_res(e: ft.FilePickerResultEvent):
            if e.files:
                for f in e.files:
                    scan_files.append(f.path)
                refresh_scan_ui()
        fp_images.on_result = on_res
        fp_images.pick_files(allow_multiple=True, allowed_extensions=["jpg", "jpeg", "png", "webp", "bmp"])

    def clear_scan_imgs(_):
        scan_files.clear()
        refresh_scan_ui()

    def run_scan(_):
        if not scan_files:
            return notify("Add at least one photo or scanned image.", True)
        try:
            processed = []
            mode = scan_filter.value
            for fp in scan_files:
                img = Image.open(fp).convert("RGB")
                if mode == "enhance":
                    img = ImageOps.autocontrast(img, cutoff=2)
                elif mode == "bw":
                    img = ImageOps.grayscale(img)
                    img = ImageOps.autocontrast(img, cutoff=3)
                    img = img.point(lambda x: 0 if x < 165 else 255, "1").convert("RGB")
                processed.append(img)
            out_file = os.path.join(get_output_dir(scan_files[0]), scan_out_name.value.strip() or "deepdf_scanned.pdf")
            processed[0].save(out_file, "PDF", resolution=150.0, save_all=True, append_images=processed[1:])
            notify(f"Scanned PDF created ({len(processed)} pages): {out_file}")
        except Exception as ex:
            notify(str(ex), True)

    tab_scan = ft.Container(
        padding=16,
        content=ft.Column([
            ft.Text("8. Scan Images / Camera Photos to PDF", size=18, weight=ft.FontWeight.BOLD, color="#38bdf8"),
            ft.Row([
                ft.ElevatedButton("+ Add Camera / Gallery Photos", on_click=add_scan_imgs, bgcolor="#2563eb", color="#ffffff"),
                ft.ElevatedButton("Clear", on_click=clear_scan_imgs, bgcolor="#334155", color="#ffffff"),
            ]),
            ft.Container(content=scan_list_ui, bgcolor="#1e293b", padding=10, border_radius=8),
            scan_filter,
            scan_out_name,
            ft.ElevatedButton("Create Scanned PDF", on_click=run_scan, bgcolor="#10b981", color="#ffffff"),
        ], scroll=ft.ScrollMode.AUTO),
    )

    # =========================================================================
    # HEADER, TABS & FOOTER LAYOUT
    # =========================================================================
    header = ft.Container(
        bgcolor="#090d16",
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        content=ft.Column([
            ft.Text("DeePDF Studio", size=22, weight=ft.FontWeight.BOLD, color="#38bdf8"),
            ft.Text(
                "Developed by Deepanshu Arya using AI and Python",
                size=12,
                weight=ft.FontWeight.BOLD,
                color="#fbbf24",
            ),
        ], spacing=2),
    )

    tabs = ft.Tabs(
        selected_index=0,
        scrollable=True,
        expand=True,
        tabs=[
            ft.Tab(text="1. Add Pages", content=tab_add),
            ft.Tab(text="2. Delete Pages", content=tab_del),
            ft.Tab(text="3. Organize", content=tab_org),
            ft.Tab(text="4. Compress", content=tab_comp),
            ft.Tab(text="5. Merge PDFs", content=tab_merge),
            ft.Tab(text="6. Unlock PDF", content=tab_unlock),
            ft.Tab(text="7. Protect PDF", content=tab_protect),
            ft.Tab(text="8. Scan to PDF", content=tab_scan),
        ],
    )

    footer = ft.Container(
        bgcolor="#090d16",
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        content=ft.Column([
            status_text,
            ft.Text(
                "Developed by Deepanshu Arya using AI and Python",
                size=11,
                italic=True,
                color="#38bdf8",
            ),
        ], spacing=2),
    )

    page.add(header, tabs, footer)


ft.app(target=main)